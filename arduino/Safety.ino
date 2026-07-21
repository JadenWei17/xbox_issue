// Active braking, E-STOP, and non-blocking ultrasonic sensing.

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


void requestEstop(EstopSource source) {
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

  if (source == ESTOP_SOURCE_GPIO17) {
    Serial.println("ESTOP source=GPIO17");
  }
}


void recordInvalidUltrasonicMeasurement() {
  ultrasonicHasValidDistance = false;
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
