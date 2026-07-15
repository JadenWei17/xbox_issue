// Motor Shield V1 output and encoder interrupt handling.

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

