/*
 * Four-motor differential-drive controller for Adafruit Motor Shield V1.
 * Controls the shield hardware directly with Arduino core functions.
 *
 * Raspberry Pi serial protocol (115200 baud):
 *   L:<left speed>,R:<right speed>\n
 * Speeds are signed integers in [-255, 255]. Motor layout:
 *   front-left M1, rear-left M2, front-right M4, rear-right M3.
 * A serial watchdog stops all motors on link loss.
 */

const unsigned long SERIAL_BAUDRATE = 115200;
const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long STATUS_INTERVAL_MS = 1000;
const size_t COMMAND_BUFFER_SIZE = 32;
const uint8_t ESTOP_PIN = 18;
const unsigned long ESTOP_CONFIRM_MS = 10;
const uint8_t LEFT_ENCODER_PIN = 2;
const uint8_t RIGHT_ENCODER_PIN = 19;
const uint8_t ULTRASONIC_TRIG_PIN = 22;
const uint8_t ULTRASONIC_ECHO_PIN = 23;
const unsigned long ULTRASONIC_INTERVAL_MS = 50;
const unsigned int EMERGENCY_DISTANCE_CM = 30;
const uint8_t ULTRASONIC_CONFIRM_COUNT = 2;
const unsigned long ULTRASONIC_TIMEOUT_US = 30000;
const unsigned long ULTRASONIC_WARNING_INTERVAL_MS = 5000;
const unsigned long ULTRASONIC_US_PER_CM = 58;
const uint8_t ACTIVE_BRAKE_PWM = 255;
const unsigned long ACTIVE_BRAKE_DURATION_MS = 200;
const unsigned long ENCODER_DEBOUNCE_MS = 50;
const unsigned int COUNTS_PER_REVOLUTION = 4;
const float WHEEL_CIRCUMFERENCE_CM = 21.8f;
const float DISTANCE_PER_COUNT_CM =
    WHEEL_CIRCUMFERENCE_CM / COUNTS_PER_REVOLUTION;
const uint8_t SPEED_LEVEL_PWM[3] = {85, 170, 255};
const uint8_t DISTANCE_START_BOOST_PWM = 200;
const unsigned long DISTANCE_START_BOOST_MS = 150;
const unsigned long DISTANCE_STALL_TIMEOUT_MS = 3000;
const uint8_t DISTANCE_SYNC_PWM_PER_COUNT = 5;
const uint8_t DISTANCE_SYNC_MAX_CORRECTION = 25;
const uint8_t DISTANCE_SYNC_MIN_PWM = 40;

// Adafruit Motor Shield V1 74HC595 control pins.
const uint8_t MOTOR_LATCH_PIN = 12;
const uint8_t MOTOR_CLOCK_PIN = 4;
const uint8_t MOTOR_ENABLE_PIN = 7;
const uint8_t MOTOR_DATA_PIN = 8;

// PWM pins for shield outputs M1, M2, M3 and M4.
const uint8_t MOTOR_PWM_PINS[4] = {11, 3, 6, 5};

// Direction-bit positions in the shield's 74HC595 register.
const uint8_t MOTOR_A_BITS[4] = {2, 1, 5, 0};
const uint8_t MOTOR_B_BITS[4] = {3, 4, 7, 6};

// Physical mounting direction for M1, M2, M3 and M4. The installation
// direction is currently unknown. After a low-speed forward test, change the
// corresponding value to true for each wheel that turns backward.
const bool MOTOR_REVERSED[4] = {false, false, false, false};

// Array indexes corresponding to the shield's M1..M4 outputs.
const size_t MOTOR_M1 = 0;
const size_t MOTOR_M2 = 1;
const size_t MOTOR_M3 = 2;
const size_t MOTOR_M4 = 3;

char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;
bool commandOverflow = false;
unsigned long lastValidCommandMs = 0;
unsigned long lastStatusMs = 0;
bool watchdogStopped = true;
volatile bool estopInterruptRequested = false;
volatile unsigned long estopInterruptRequestedAtMs = 0;
bool estopLatched = false;
uint8_t motorLatchState = 0;
int lastLeftSpeed = 0;
int lastRightSpeed = 0;
volatile unsigned long leftEncoderCount = 0;
volatile unsigned long rightEncoderCount = 0;
volatile unsigned long leftPreviousPulseMs = 0;
volatile unsigned long rightPreviousPulseMs = 0;
unsigned long distanceTargetCount = 0;
bool donePending = false;
bool distanceLeftDone = false;
bool distanceRightDone = false;
int distanceCruiseSpeed = 0;
unsigned long distanceBoostEndsAtMs = 0;
bool distanceBoostActive = false;
unsigned long leftLastProgressMs = 0;
unsigned long rightLastProgressMs = 0;
unsigned long leftPreviousCheckedCount = 0;
unsigned long rightPreviousCheckedCount = 0;
unsigned long nextUltrasonicMeasurementMs = 0;
unsigned long ultrasonicPhaseStartedUs = 0;
unsigned long ultrasonicEchoRiseUs = 0;
unsigned int latestUltrasonicDistanceCm = 0;
bool ultrasonicHasValidDistance = false;
uint8_t ultrasonicTooCloseCount = 0;
unsigned long ultrasonicFailureCount = 0;
unsigned long lastUltrasonicWarningMs = 0;
bool activeBrakeEngaged = false;
unsigned long activeBrakeReleaseMs = 0;

enum RobotState {
  IDLE,
  MANUAL,
  DISTANCE_MOVE,
  ESTOP
};

RobotState robotState = IDLE;

enum EstopSource {
  ESTOP_SOURCE_NONE,
  ESTOP_SOURCE_GPIO17,
  ESTOP_SOURCE_ULTRASONIC
};

enum UltrasonicPhase {
  ULTRASONIC_IDLE,
  ULTRASONIC_TRIGGER_HIGH,
  ULTRASONIC_WAIT_RISE,
  ULTRASONIC_WAIT_FALL
};

EstopSource estopSource = ESTOP_SOURCE_NONE;
UltrasonicPhase ultrasonicPhase = ULTRASONIC_IDLE;


void requestGpioEstopInterrupt() {
  estopInterruptRequested = true;
  estopInterruptRequestedAtMs = millis();
}


void countLeftEncoder() {
  unsigned long now = millis();
  if (now - leftPreviousPulseMs > ENCODER_DEBOUNCE_MS) {
    ++leftEncoderCount;
    leftPreviousPulseMs = now;
  }
}


void countRightEncoder() {
  unsigned long now = millis();
  if (now - rightPreviousPulseMs > ENCODER_DEBOUNCE_MS) {
    ++rightEncoderCount;
    rightPreviousPulseMs = now;
  }
}


void writeMotorLatch() {
  digitalWrite(MOTOR_LATCH_PIN, LOW);
  shiftOut(MOTOR_DATA_PIN, MOTOR_CLOCK_PIN, MSBFIRST, motorLatchState);
  digitalWrite(MOTOR_LATCH_PIN, HIGH);
}


void setLatchBit(uint8_t bitPosition, bool enabled) {
  if (enabled) {
    motorLatchState |= (uint8_t)(1U << bitPosition);
  } else {
    motorLatchState &= (uint8_t)~(1U << bitPosition);
  }
}


void setMotor(size_t index, int speedValue) {
  speedValue = constrain(speedValue, -255, 255);

  if (speedValue == 0) {
    analogWrite(MOTOR_PWM_PINS[index], 0);
    setLatchBit(MOTOR_A_BITS[index], false);
    setLatchBit(MOTOR_B_BITS[index], false);
    writeMotorLatch();
    return;
  }

  bool forward = speedValue > 0;
  if (MOTOR_REVERSED[index]) {
    forward = !forward;
  }

  setLatchBit(MOTOR_A_BITS[index], forward);
  setLatchBit(MOTOR_B_BITS[index], !forward);
  writeMotorLatch();
  analogWrite(MOTOR_PWM_PINS[index], (uint8_t)abs(speedValue));
}


void setDriveSpeeds(int leftSpeed, int rightSpeed) {
  setMotor(MOTOR_M1, leftSpeed);   // Front-left
  setMotor(MOTOR_M2, leftSpeed);   // Rear-left
  setMotor(MOTOR_M4, rightSpeed);  // Front-right
  setMotor(MOTOR_M3, rightSpeed);  // Rear-right
}


void setLeftSpeed(int speedValue) {
  setMotor(MOTOR_M1, speedValue);
  setMotor(MOTOR_M2, speedValue);
}


void setRightSpeed(int speedValue) {
  setMotor(MOTOR_M4, speedValue);
  setMotor(MOTOR_M3, speedValue);
}


void stopAllMotors() {
  setDriveSpeeds(0, 0);
}


void startActiveBrake() {
  // L293D dynamic braking: both direction inputs LOW while Enable is HIGH.
  for (size_t index = 0; index < 4; ++index) {
    setLatchBit(MOTOR_A_BITS[index], false);
    setLatchBit(MOTOR_B_BITS[index], false);
  }
  writeMotorLatch();
  for (size_t index = 0; index < 4; ++index) {
    analogWrite(MOTOR_PWM_PINS[index], ACTIVE_BRAKE_PWM);
  }
  activeBrakeEngaged = true;
  activeBrakeReleaseMs = millis() + ACTIVE_BRAKE_DURATION_MS;
}


void updateActiveBrake() {
  if (!activeBrakeEngaged ||
      (long)(millis() - activeBrakeReleaseMs) < 0) {
    return;
  }
  activeBrakeEngaged = false;
  stopAllMotors();
}


bool isMovingForward() {
  if (robotState == MANUAL) {
    return (long)lastLeftSpeed + (long)lastRightSpeed > 0;
  }
  return robotState == DISTANCE_MOVE && distanceCruiseSpeed > 0;
}


void requestEstop(EstopSource source, unsigned int distanceCm = 0) {
  if (estopLatched) {
    return;
  }
  estopLatched = true;
  estopSource = source;
  startActiveBrake();
  lastLeftSpeed = 0;
  lastRightSpeed = 0;
  watchdogStopped = true;
  robotState = ESTOP;
  donePending = false;
  distanceBoostActive = false;

  if (source == ESTOP_SOURCE_ULTRASONIC) {
    Serial.print("ESTOP source=ULTRASONIC distance_cm=");
    Serial.println(distanceCm);
  } else if (source == ESTOP_SOURCE_GPIO17) {
    Serial.println("ESTOP source=GPIO17");
  }
}


void recordInvalidUltrasonicMeasurement() {
  ultrasonicHasValidDistance = false;
  ultrasonicTooCloseCount = 0;
  ++ultrasonicFailureCount;
  unsigned long now = millis();
  if (now - lastUltrasonicWarningMs >= ULTRASONIC_WARNING_INTERVAL_MS) {
    lastUltrasonicWarningMs = now;
    Serial.print("WARN ULTRASONIC_NO_ECHO failures=");
    Serial.println(ultrasonicFailureCount);
  }
}


void recordValidUltrasonicMeasurement(unsigned long echoDurationUs) {
  unsigned int distanceCm =
      (unsigned int)(echoDurationUs / ULTRASONIC_US_PER_CM);
  if (distanceCm == 0) {
    recordInvalidUltrasonicMeasurement();
    return;
  }

  latestUltrasonicDistanceCm = distanceCm;
  ultrasonicHasValidDistance = true;
  ultrasonicFailureCount = 0;

  if (!isMovingForward()) {
    ultrasonicTooCloseCount = 0;
    return;
  }
  if (distanceCm < EMERGENCY_DISTANCE_CM) {
    if (ultrasonicTooCloseCount < ULTRASONIC_CONFIRM_COUNT) {
      ++ultrasonicTooCloseCount;
    }
    if (ultrasonicTooCloseCount >= ULTRASONIC_CONFIRM_COUNT) {
      requestEstop(ESTOP_SOURCE_ULTRASONIC, distanceCm);
    }
  } else {
    ultrasonicTooCloseCount = 0;
  }
}


void updateUltrasonic() {
  unsigned long nowUs = micros();
  unsigned long nowMs = millis();

  if (ultrasonicPhase == ULTRASONIC_IDLE) {
    if ((long)(nowMs - nextUltrasonicMeasurementMs) < 0) {
      return;
    }
    digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
    ultrasonicPhaseStartedUs = nowUs;
    ultrasonicPhase = ULTRASONIC_TRIGGER_HIGH;
    return;
  }

  if (ultrasonicPhase == ULTRASONIC_TRIGGER_HIGH) {
    if (nowUs - ultrasonicPhaseStartedUs >= 10) {
      digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
      ultrasonicPhaseStartedUs = nowUs;
      ultrasonicPhase = ULTRASONIC_WAIT_RISE;
    }
    return;
  }

  if (ultrasonicPhase == ULTRASONIC_WAIT_RISE) {
    if (digitalRead(ULTRASONIC_ECHO_PIN) == HIGH) {
      ultrasonicEchoRiseUs = nowUs;
      ultrasonicPhase = ULTRASONIC_WAIT_FALL;
    } else if (nowUs - ultrasonicPhaseStartedUs >= ULTRASONIC_TIMEOUT_US) {
      recordInvalidUltrasonicMeasurement();
      ultrasonicPhase = ULTRASONIC_IDLE;
      nextUltrasonicMeasurementMs = nowMs + ULTRASONIC_INTERVAL_MS;
    }
    return;
  }

  if (digitalRead(ULTRASONIC_ECHO_PIN) == LOW) {
    recordValidUltrasonicMeasurement(nowUs - ultrasonicEchoRiseUs);
    ultrasonicPhase = ULTRASONIC_IDLE;
    nextUltrasonicMeasurementMs = nowMs + ULTRASONIC_INTERVAL_MS;
  } else if (nowUs - ultrasonicEchoRiseUs >= ULTRASONIC_TIMEOUT_US) {
    recordInvalidUltrasonicMeasurement();
    ultrasonicPhase = ULTRASONIC_IDLE;
    nextUltrasonicMeasurementMs = nowMs + ULTRASONIC_INTERVAL_MS;
  }
}


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


void startDistanceMove(bool forward, int speedLevel,
                       unsigned long distanceCm) {
  noInterrupts();
  leftEncoderCount = 0;
  rightEncoderCount = 0;
  leftPreviousPulseMs = 0;
  rightPreviousPulseMs = 0;
  interrupts();

  distanceTargetCount = (unsigned long)ceilf(
      ((float)distanceCm) / DISTANCE_PER_COUNT_CM);
  if (distanceTargetCount < 1) {
    distanceTargetCount = 1;
  }
  donePending = false;
  distanceLeftDone = false;
  distanceRightDone = false;
  int speedValue = SPEED_LEVEL_PWM[speedLevel - 1];
  if (!forward) {
    speedValue = -speedValue;
  }
  distanceCruiseSpeed = speedValue;
  int boostSpeed = speedValue;
  if (abs(boostSpeed) < DISTANCE_START_BOOST_PWM) {
    boostSpeed = forward ? DISTANCE_START_BOOST_PWM
                         : -DISTANCE_START_BOOST_PWM;
  }
  unsigned long now = millis();
  distanceBoostEndsAtMs = now + DISTANCE_START_BOOST_MS;
  distanceBoostActive = true;
  leftLastProgressMs = now;
  rightLastProgressMs = now;
  leftPreviousCheckedCount = 0;
  rightPreviousCheckedCount = 0;
  setDriveSpeeds(boostSpeed, boostSpeed);
  lastLeftSpeed = boostSpeed;
  lastRightSpeed = boostSpeed;
  watchdogStopped = false;
  robotState = DISTANCE_MOVE;
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
  if (*cursor < '1' || *cursor > '3') {
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


void applyDistanceSynchronization(unsigned long leftCount,
                                  unsigned long rightCount) {
  if (distanceLeftDone || distanceRightDone || distanceBoostActive) {
    return;
  }

  long countError = (long)rightCount - (long)leftCount;
  long correction = countError * DISTANCE_SYNC_PWM_PER_COUNT;
  correction = constrain(
      correction,
      -(long)DISTANCE_SYNC_MAX_CORRECTION,
      (long)DISTANCE_SYNC_MAX_CORRECTION);

  int directionSign = distanceCruiseSpeed >= 0 ? 1 : -1;
  int basePwm = abs(distanceCruiseSpeed);
  int leftPwm = constrain(
      basePwm + (int)correction, DISTANCE_SYNC_MIN_PWM, 255);
  int rightPwm = constrain(
      basePwm - (int)correction, DISTANCE_SYNC_MIN_PWM, 255);
  int leftSpeed = directionSign * leftPwm;
  int rightSpeed = directionSign * rightPwm;

  if (leftSpeed != lastLeftSpeed || rightSpeed != lastRightSpeed) {
    setDriveSpeeds(leftSpeed, rightSpeed);
    lastLeftSpeed = leftSpeed;
    lastRightSpeed = rightSpeed;
  }
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
    robotState = IDLE;
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    donePending = false;
    lastValidCommandMs = millis();
    watchdogStopped = true;
    return true;
  }

  if (estopLatched || estopInterruptRequested) {
    return false;
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

  setDriveSpeeds(leftSpeed, rightSpeed);
  lastLeftSpeed = leftSpeed;
  lastRightSpeed = rightSpeed;
  lastValidCommandMs = millis();
  watchdogStopped = false;
  robotState = MANUAL;
  return true;
}


void updateDistanceMove() {
  if (robotState != DISTANCE_MOVE) {
    return;
  }

  noInterrupts();
  unsigned long leftCount = leftEncoderCount;
  unsigned long rightCount = rightEncoderCount;
  interrupts();

  unsigned long now = millis();
  bool countsChanged = false;
  if (leftCount != leftPreviousCheckedCount) {
    leftPreviousCheckedCount = leftCount;
    leftLastProgressMs = now;
    countsChanged = true;
  }
  if (rightCount != rightPreviousCheckedCount) {
    rightPreviousCheckedCount = rightCount;
    rightLastProgressMs = now;
    countsChanged = true;
  }

  if (distanceBoostActive &&
      (long)(now - distanceBoostEndsAtMs) >= 0) {
    distanceBoostActive = false;
    if (!distanceLeftDone) {
      setLeftSpeed(distanceCruiseSpeed);
      lastLeftSpeed = distanceCruiseSpeed;
    }
    if (!distanceRightDone) {
      setRightSpeed(distanceCruiseSpeed);
      lastRightSpeed = distanceCruiseSpeed;
    }
  }

  if (countsChanged) {
    applyDistanceSynchronization(leftCount, rightCount);
  }

  if (!distanceLeftDone && leftCount >= distanceTargetCount) {
    setLeftSpeed(0);
    lastLeftSpeed = 0;
    distanceLeftDone = true;
  }
  if (!distanceRightDone && rightCount >= distanceTargetCount) {
    setRightSpeed(0);
    lastRightSpeed = 0;
    distanceRightDone = true;
  }
  if (distanceLeftDone && distanceRightDone) {
    stopAllMotors();
    watchdogStopped = true;
    robotState = IDLE;
    donePending = true;
    return;
  }

  bool leftStalled = !distanceLeftDone &&
      now - leftLastProgressMs >= DISTANCE_STALL_TIMEOUT_MS;
  bool rightStalled = !distanceRightDone &&
      now - rightLastProgressMs >= DISTANCE_STALL_TIMEOUT_MS;
  if (leftStalled || rightStalled) {
    stopAllMotors();
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    watchdogStopped = true;
    robotState = IDLE;
    if (leftStalled && rightStalled) {
      Serial.println("ERR STALL BOTH");
    } else if (leftStalled) {
      Serial.println("ERR STALL LEFT");
    } else {
      Serial.println("ERR STALL RIGHT");
    }
  }
}


void sendDoneIfPossible() {
  if (donePending && Serial.availableForWrite() >= 6) {
    Serial.println("DONE");
    donePending = false;
  }
}


void sendStatusIfPossible() {
  unsigned long now = millis();
  if (now - lastStatusMs < STATUS_INTERVAL_MS) {
    return;
  }
  lastStatusMs = now;

  // Never block motor command reception if the host is not reading replies.
  if (Serial.availableForWrite() < 48) {
    return;
  }
  if (robotState == DISTANCE_MOVE) {
    noInterrupts();
    unsigned long leftCount = leftEncoderCount;
    unsigned long rightCount = rightEncoderCount;
    interrupts();
    Serial.print("MOVE C L:");
    Serial.print(leftCount);
    Serial.print(",R:");
    Serial.print(rightCount);
    Serial.print(",T:");
    Serial.print(distanceTargetCount);
    Serial.print(" PWM L:");
    Serial.print(lastLeftSpeed);
    Serial.print(",R:");
    Serial.println(lastRightSpeed);
    return;
  }
  Serial.print(robotState == ESTOP ? "ESTOP L:" :
               (watchdogStopped ? "STOP L:" : "OK L:"));
  Serial.print(lastLeftSpeed);
  Serial.print(",R:");
  Serial.println(lastRightSpeed);
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
        if (strncmp(commandBuffer, "MOVE ", 5) == 0) {
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


void setup() {
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  pinMode(LEFT_ENCODER_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENCODER_PIN, INPUT_PULLUP);
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  pinMode(MOTOR_LATCH_PIN, OUTPUT);
  pinMode(MOTOR_CLOCK_PIN, OUTPUT);
  pinMode(MOTOR_ENABLE_PIN, OUTPUT);
  pinMode(MOTOR_DATA_PIN, OUTPUT);
  digitalWrite(MOTOR_ENABLE_PIN, LOW);

  for (size_t index = 0; index < 4; ++index) {
    pinMode(MOTOR_PWM_PINS[index], OUTPUT);
    analogWrite(MOTOR_PWM_PINS[index], 0);
  }
  motorLatchState = 0;
  writeMotorLatch();
  stopAllMotors();
  if (digitalRead(ESTOP_PIN) == LOW) {
    estopInterruptRequested = true;
  }
  attachInterrupt(
      digitalPinToInterrupt(ESTOP_PIN), requestGpioEstopInterrupt, FALLING);
  attachInterrupt(
      digitalPinToInterrupt(LEFT_ENCODER_PIN), countLeftEncoder, FALLING);
  attachInterrupt(
      digitalPinToInterrupt(RIGHT_ENCODER_PIN), countRightEncoder, FALLING);
  Serial.begin(SERIAL_BAUDRATE);
  Serial.println("READY");
  lastValidCommandMs = millis();
}


void loop() {
  noInterrupts();
  bool estopRequested = estopInterruptRequested;
  unsigned long estopRequestedAtMs = estopInterruptRequestedAtMs;
  interrupts();

  if (estopRequested &&
      millis() - estopRequestedAtMs >= ESTOP_CONFIRM_MS) {
    bool confirmed = digitalRead(ESTOP_PIN) == LOW;
    noInterrupts();
    estopInterruptRequested = false;
    interrupts();
    if (confirmed) {
      requestEstop(ESTOP_SOURCE_GPIO17);
    }
  }

  updateUltrasonic();
  readSerialCommands();

  updateDistanceMove();
  updateActiveBrake();

  if (robotState == MANUAL && !watchdogStopped &&
      millis() - lastValidCommandMs > COMMAND_TIMEOUT_MS) {
    stopAllMotors();
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    watchdogStopped = true;
    robotState = IDLE;
    Serial.println("WATCHDOG");
  }

  sendDoneIfPossible();
  sendStatusIfPossible();
}
