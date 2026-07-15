#include <Wire.h>
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

#include "Config.h"
#include "Types.h"

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
bool piAvoidanceMode = false;
uint8_t ultrasonicTooCloseCount = 0;
unsigned long ultrasonicFailureCount = 0;
unsigned long lastUltrasonicWarningMs = 0;
bool activeBrakeEngaged = false;
unsigned long activeBrakeReleaseMs = 0;

RobotState robotState = IDLE;
RobotPose pose={0,0,0,0,0,0,0,0};
PIDController distancePid,headingPid,turnPid;
float gyroBias=0, targetDistanceCm=0, targetHeadingTotalDeg=0;
float startLeftDistanceCm=0,startRightDistanceCm=0,previousLeftDistanceCm=0,previousRightDistanceCm=0,previousHeadingTotalDeg=0;
unsigned long previousLeftEncoderCount=0,previousRightEncoderCount=0;
unsigned long lastMotionUs=0,motionStartMs=0,motionTimeoutMs=0;
unsigned long lastMpuUpdateUs=0;
unsigned long lastControllerUs=0;
uint8_t motionSpeedLevel=1,stableCycles=0;
int requestedLeftPwm=0,requestedRightPwm=0;

EstopSource estopSource = ESTOP_SOURCE_NONE;
UltrasonicPhase ultrasonicPhase = ULTRASONIC_IDLE;

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
  distancePid.configure(DISTANCE_KP,DISTANCE_KI,DISTANCE_KD,-255,255,-100,100);
  headingPid.configure(HEADING_KP,HEADING_KI,HEADING_KD,-100,100,-50,50);
  turnPid.configure(TURN_KP,TURN_KI,TURN_KD,-255,255,-100,100);
  initializeMpu();
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
      requestEstop(ESTOP_SOURCE_GPIO17, 0);
    }
  }

  updateUltrasonic();
  readSerialCommands();
  updateNavigation();
  if (robotState==DISTANCE_MOVE || robotState==TURN_IN_PLACE) updateClosedLoop();
  else updateDistanceMove();
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
