/*
 * Four-motor differential-drive controller for Adafruit Motor Shield V1.
 * Controls the shield hardware directly with Arduino core functions.
 *
 * Raspberry Pi serial protocol (115200 baud):
 *   L:<left speed>,R:<right speed>\n
 * Speeds are signed integers in [-255, 255]. Motor layout:
 *   front-left M3, rear-left M4, front-right M2, rear-right M1.
 * A serial watchdog stops all motors on link loss.
 */

const unsigned long SERIAL_BAUDRATE = 115200;
const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long STATUS_INTERVAL_MS = 1000;
const size_t COMMAND_BUFFER_SIZE = 32;
const uint8_t ESTOP_PIN = 18;

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
bool estopLatched = false;
uint8_t motorLatchState = 0;
int lastLeftSpeed = 0;
int lastRightSpeed = 0;


void requestEstop() {
  estopInterruptRequested = true;
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
  setMotor(MOTOR_M3, leftSpeed);   // Front-left
  setMotor(MOTOR_M4, leftSpeed);   // Rear-left
  setMotor(MOTOR_M2, rightSpeed);  // Front-right
  setMotor(MOTOR_M1, rightSpeed);  // Rear-right
}


void stopAllMotors() {
  setDriveSpeeds(0, 0);
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


bool applyCommand(const char *command) {
  if (strcmp(command, "RESET") == 0) {
    estopLatched = false;
    lastValidCommandMs = millis();
    watchdogStopped = true;
    return true;
  }

  if (estopLatched || estopInterruptRequested) {
    return false;
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
  return true;
}


void sendStatusIfPossible() {
  unsigned long now = millis();
  if (now - lastStatusMs < STATUS_INTERVAL_MS) {
    return;
  }
  lastStatusMs = now;

  // Never block motor command reception if the host is not reading replies.
  if (Serial.availableForWrite() < 24) {
    return;
  }
  Serial.print(watchdogStopped ? "STOP L:" : "OK L:");
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
        applyCommand(commandBuffer);
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
  attachInterrupt(digitalPinToInterrupt(ESTOP_PIN), requestEstop, FALLING);
  Serial.begin(SERIAL_BAUDRATE);
  Serial.println("READY");
  lastValidCommandMs = millis();
}


void loop() {
  noInterrupts();
  bool handleEstop = estopInterruptRequested;
  estopInterruptRequested = false;
  interrupts();

  if (handleEstop) {
    estopLatched = true;
    stopAllMotors();
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    watchdogStopped = true;
  }

  readSerialCommands();

  if (!watchdogStopped &&
      millis() - lastValidCommandMs > COMMAND_TIMEOUT_MS) {
    stopAllMotors();
    lastLeftSpeed = 0;
    lastRightSpeed = 0;
    watchdogStopped = true;
  }

  sendStatusIfPossible();
}
