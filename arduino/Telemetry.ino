// Non-blocking completion and status messages.

void sendDoneIfPossible() {
  if (donePending && Serial.availableForWrite() >= 6) {
    Serial.println("DONE");
    donePending = false;
  }
}


void sendStatusIfPossible() {
  unsigned long now = millis();
  if (now - lastStatusMs < TELEMETRY_INTERVAL_MS) {
    return;
  }
  lastStatusMs = now;

  // Never block motor command reception if the host is not reading replies.
  if (Serial.availableForWrite() < 48) {
    return;
  }
  const char *modeName = "IDLE";
  if (robotState == MANUAL) modeName = "MANUAL";
  else if (robotState == DISTANCE_MOVE) modeName = "MOVE";
  else if (robotState == TURN_IN_PLACE) modeName = "TURN";
  else if (robotState == ESTOP) modeName = "ESTOP";
  Serial.print("STATE,MODE=");Serial.print(modeName);
  Serial.print(",X=");Serial.print(pose.xCm,1);Serial.print(",Y=");Serial.print(pose.yCm,1);
  Serial.print(",H=");Serial.print(pose.headingDeg,1);Serial.print(",HT=");Serial.print(pose.headingTotalDeg,1);
  Serial.print(",L=");Serial.print(pose.leftDistanceCm,1);Serial.print(",R=");Serial.print(pose.rightDistanceCm,1);
  Serial.print(",V=");Serial.print(pose.linearVelocityCmS,1);Serial.print(",W=");Serial.print(pose.angularVelocityDegS,1);
  Serial.print(",US=");
  if (ultrasonicHasValidDistance) Serial.print(latestUltrasonicDistanceCm);
  else Serial.print("NA");
  Serial.print(",LPWM=");Serial.print(lastLeftSpeed);Serial.print(",RPWM=");Serial.println(lastRightSpeed);
}

