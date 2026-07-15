// Serial command parsing and command dispatch.

bool parseMotorSpeed(const char *&cursor, int &speedValue) {
  bool negative = false;
  if (*cursor == '-') {
    negative = true;
    ++cursor;
  }

  if (*cursor < '0' || *cursor > '9') {
    return false;
  }

  int value = 0;
  while (*cursor >= '0' && *cursor <= '9') {
    value = value * 10 + (*cursor - '0');
    if (value > 255) {
      return false;
    }
    ++cursor;
  }

  speedValue = negative ? -value : value;
  return true;
}


bool consumeText(const char *&cursor, const char *expected) {
  while (*expected != '\0') {
    if (*cursor != *expected) {
      return false;
    }
    ++cursor;
    ++expected;
  }
  return true;
}


bool parseUnsignedLong(const char *&cursor, unsigned long &value) {
  if (*cursor < '0' || *cursor > '9') {
    return false;
  }
  value = 0;
  while (*cursor >= '0' && *cursor <= '9') {
    unsigned long digit = (unsigned long)(*cursor - '0');
    if (value > (1000UL - digit) / 10UL) {
      return false;
    }
    value = value * 10UL + digit;
    ++cursor;
  }
  return true;
}


bool parsePositiveFloat(const char *&cursor, float &value) {
  if (*cursor < '0' || *cursor > '9') {
    return false;
  }
  unsigned long whole = 0;
  while (*cursor >= '0' && *cursor <= '9') {
    unsigned long digit = (unsigned long)(*cursor - '0');
    if (whole > (1000UL - digit) / 10UL) {
      return false;
    }
    whole = whole * 10UL + digit;
    ++cursor;
  }
  float fraction = 0.0f;
  float place = 0.1f;
  if (*cursor == '.') {
    ++cursor;
    if (*cursor < '0' || *cursor > '9') {
      return false;
    }
    while (*cursor >= '0' && *cursor <= '9') {
      fraction += (float)(*cursor - '0') * place;
      place *= 0.1f;
      ++cursor;
    }
  }
  value = (float)whole + fraction;
  return value > 0.0f;
}

bool parseAndStartDistanceMove(const char *command) {
  const char *cursor = command;
  if (!consumeText(cursor, "MOVE ")) {
    return false;
  }
  bool forward;
  if (consumeText(cursor, "FWD ")) {
    forward = true;
  } else {
    cursor = command + 5;
    if (!consumeText(cursor, "BWD ")) {
      return false;
    }
    forward = false;
  }
  if (*cursor < '1' || *cursor > '2') {
    return false;
  }
  int speedLevel = *cursor - '0';
  ++cursor;
  if (*cursor != ' ') {
    return false;
  }
  ++cursor;
  unsigned long distanceCm = 0;
  if (!parseUnsignedLong(cursor, distanceCm) || *cursor != '\0') {
    return false;
  }
  if (distanceCm < 1 || distanceCm > 1000) {
    return false;
  }
  startDistanceMove(forward, speedLevel, distanceCm);
  return true;
}

bool applyCommand(const char *command) {
  if (strcmp(command, "RESET") == 0) {
    if (digitalRead(ESTOP_PIN) == LOW) {
      return false;
    }
    activeBrakeEngaged = false;
    stopAllMotors();
    estopLatched = false;
    estopSource = ESTOP_SOURCE_NONE;
    piAvoidanceMode = false;
    robotState = IDLE;
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    donePending = false;
    resetControllers();
    lastValidCommandMs = millis();
    watchdogStopped = true;
    return true;
  }

  if (strcmp(command, "IDLE") == 0) {
    stopAllMotors();
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    watchdogStopped = true;
    donePending = false;
    distanceBoostActive = false;
    resetControllers();
    if (!estopLatched && !estopInterruptRequested) {
      robotState = IDLE;
      return true;
    }
    return false;
  }

  if (estopLatched || estopInterruptRequested) {
    return false;
  }

  if (strcmp(command, "AVOID,ON") == 0) {
    piAvoidanceMode = true;
    return true;
  }
  if (strcmp(command, "AVOID,OFF") == 0) {
    piAvoidanceMode = false;
    return true;
  }

  if (strncmp(command,"MOVE,",5)==0 || strncmp(command,"TURN,",5)==0) {
    if (robotState==DISTANCE_MOVE || robotState==TURN_IN_PLACE) { Serial.println("BUSY"); return true; }
    const char *cursor = command;
    bool isMove = consumeText(cursor, "MOVE,");
    bool isTurn = false;
    if (!isMove) {
      cursor = command;
      isTurn = consumeText(cursor, "TURN,");
    }
    bool positiveDirection;
    if (isMove && consumeText(cursor, "FWD,")) positiveDirection = true;
    else if (isMove) { cursor = command + 5; if (!consumeText(cursor, "REV,")) return false; positiveDirection = false; }
    else if (isTurn && consumeText(cursor, "LEFT,")) positiveDirection = true;
    else if (isTurn) { cursor = command + 5; if (!consumeText(cursor, "RIGHT,")) return false; positiveDirection = false; }
    else return false;
    if (*cursor < '1' || *cursor > '2' || cursor[1] != ',') return false;
    int level = *cursor - '0'; cursor += 2;
    float value = 0.0f;
    if (!parsePositiveFloat(cursor, value) || *cursor != '\0' ||
        (isTurn && value > 720.0f) || (isMove && value > 1000.0f)) return false;
    stopAllMotors();lastLeftSpeed=lastRightSpeed=0;
    startLeftDistanceCm=pose.leftDistanceCm;startRightDistanceCm=pose.rightDistanceCm;motionSpeedLevel=level;motionStartMs=millis();resetControllers();
    if(isMove) {targetDistanceCm=positiveDirection?value:-value;targetHeadingTotalDeg=pose.headingTotalDeg;motionTimeoutMs=5000UL+(unsigned long)(value*250);robotState=DISTANCE_MOVE;}
    else {targetHeadingTotalDeg=pose.headingTotalDeg+(positiveDirection?value:-value);motionTimeoutMs=4000UL+(unsigned long)(value*100);robotState=TURN_IN_PLACE;}
    Serial.print("ACK,");Serial.println(command); return true;
  }

  if (strncmp(command, "MOVE ", 5) == 0) {
    return parseAndStartDistanceMove(command);
  }

  // Strictly parse: L:<integer>,R:<integer>
  if (command[0] != 'L' || command[1] != ':') {
    return false;
  }

  const char *cursor = command + 2;
  int leftSpeed;
  if (!parseMotorSpeed(cursor, leftSpeed) ||
      cursor[0] != ',' || cursor[1] != 'R' || cursor[2] != ':') {
    return false;
  }

  cursor += 3;
  int rightSpeed;
  if (!parseMotorSpeed(cursor, rightSpeed) || *cursor != '\0') {
    return false;
  }

  // Any manual Xbox command leaves keyboard avoidance mode. This prevents a
  // lost Pi process from accidentally disabling the original manual-mode
  // ultrasonic E-STOP on a later driving session.
  piAvoidanceMode = false;

  setDriveSpeeds(leftSpeed, rightSpeed);
  lastLeftSpeed = leftSpeed;
  lastRightSpeed = rightSpeed;
  lastValidCommandMs = millis();
  watchdogStopped = false;
  robotState = MANUAL;
  return true;
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();

    if (incoming == '\r') {
      continue;
    }
    if (incoming == '\n') {
      if (!commandOverflow && commandLength > 0) {
        commandBuffer[commandLength] = '\0';
        bool accepted = applyCommand(commandBuffer);
        if (strchr(commandBuffer, ',') != NULL) {
          if (!accepted) Serial.println(estopLatched ? "ERROR,ESTOP_ACTIVE" : "ERROR,INVALID_COMMAND");
        } else if (strncmp(commandBuffer, "MOVE ", 5) == 0) {
          if (accepted) {
            Serial.println("ACK MOVE");
          } else if (estopLatched || estopInterruptRequested) {
            Serial.println("ERR ESTOP");
          } else {
            Serial.println("ERR COMMAND");
          }
        } else if (strcmp(commandBuffer, "RESET") == 0) {
          if (accepted) {
            Serial.println("ACK RESET");
          } else {
            Serial.println("ERR ESTOP");
          }
        } else if (strcmp(commandBuffer, "IDLE") == 0) {
          Serial.println(accepted ? "ACK IDLE" : "ERR ESTOP");
        }
      }
      commandLength = 0;
      commandOverflow = false;
      continue;
    }

    if (commandOverflow) {
      continue;
    }
    if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = incoming;
    } else {
      commandLength = 0;
      commandOverflow = true;
    }
  }
}
