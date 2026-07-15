// PID control and encoder-based distance/turn actions.

int effectivePwm(float value,int limit){int p=constrain((int)value,-limit,limit);if(p && abs(p)<MIN_EFFECTIVE_PWM)p=p>0?MIN_EFFECTIVE_PWM:-MIN_EFFECTIVE_PWM;return p;}
int rampPwm(int current,int target){return current+constrain(target-current,-MAX_PWM_STEP,MAX_PWM_STEP);}
void resetControllers(){distancePid.reset();headingPid.reset();turnPid.reset();stableCycles=0;requestedLeftPwm=requestedRightPwm=0;lastControllerUs=micros();}
void finishMotion(const char *kind){stopAllMotors();lastLeftSpeed=lastRightSpeed=0;robotState=IDLE;resetControllers();Serial.print("DONE,");Serial.println(kind);}

void updateClosedLoop(){
 if(robotState!=DISTANCE_MOVE&&robotState!=TURN_IN_PLACE)return;
 if(millis()-motionStartMs>motionTimeoutMs){stopAllMotors();lastLeftSpeed=lastRightSpeed=0;robotState=IDLE;resetControllers();Serial.println("ERROR,TIMEOUT");return;}
 unsigned long nowUs=micros();if(nowUs-lastControllerUs<20000UL)return;float dt=(nowUs-lastControllerUs)*1e-6f;lastControllerUs=nowUs;
 float error=0;
 int limit = robotState == TURN_IN_PLACE
     ? TURN_SPEED_LEVEL_PWM[motionSpeedLevel - 1]
     : MOVE_SPEED_LEVEL_PWM[motionSpeedLevel - 1];
 if(robotState==DISTANCE_MOVE){float travelled=0.5f*((pose.leftDistanceCm-startLeftDistanceCm)+(pose.rightDistanceCm-startRightDistanceCm));error=targetDistanceCm-travelled;if(fabs(error)<=DISTANCE_TOLERANCE_CM){requestedLeftPwm=requestedRightPwm=0;lastLeftSpeed=lastRightSpeed=0;stopAllMotors();stableCycles++;if(stableCycles>=TARGET_STABLE_CYCLES)finishMotion("MOVE");return;}stableCycles=0;float headingError=targetHeadingTotalDeg-pose.headingTotalDeg;float base=distancePid.update(error,dt),correction=headingPid.update(headingError,dt);requestedLeftPwm=effectivePwm(base-correction,limit);requestedRightPwm=effectivePwm(base+correction,limit);}
 else {error=targetHeadingTotalDeg-pose.headingTotalDeg;if(fabs(error)<=ANGLE_TOLERANCE_DEG){requestedLeftPwm=requestedRightPwm=0;lastLeftSpeed=lastRightSpeed=0;stopAllMotors();if(fabs(pose.angularVelocityDegS)<=ANGULAR_VELOCITY_TOLERANCE)stableCycles++;else stableCycles=0;if(stableCycles>=TARGET_STABLE_CYCLES)finishMotion("TURN");return;}stableCycles=0;int turn=effectivePwm(turnPid.update(error,dt),limit);requestedLeftPwm=-turn;requestedRightPwm=turn;}
 lastLeftSpeed=rampPwm(lastLeftSpeed,requestedLeftPwm);lastRightSpeed=rampPwm(lastRightSpeed,requestedRightPwm);setDriveSpeeds(lastLeftSpeed,lastRightSpeed);
}

void startDistanceMove(bool forward, int speedLevel,
                       unsigned long distanceCm) {
  stopAllMotors();
  lastLeftSpeed = lastRightSpeed = 0;
  startLeftDistanceCm=pose.leftDistanceCm;startRightDistanceCm=pose.rightDistanceCm;
  targetDistanceCm=forward?(float)distanceCm:-(float)distanceCm;
  targetHeadingTotalDeg=pose.headingTotalDeg;
  motionSpeedLevel=speedLevel;motionStartMs=millis();
  motionTimeoutMs=5000UL+distanceCm*250UL;resetControllers();

  distanceTargetCount = (unsigned long)ceilf(
      ((float)distanceCm) / DISTANCE_PER_COUNT_CM);
  if (distanceTargetCount < 1) {
    distanceTargetCount = 1;
  }
  donePending = false;
  distanceLeftDone = false;
  distanceRightDone = false;
  int speedValue = MOVE_SPEED_LEVEL_PWM[speedLevel - 1];
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

