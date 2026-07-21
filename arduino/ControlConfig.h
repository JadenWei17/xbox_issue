#pragma once

#include <Arduino.h>

// MPU6500 and navigation sampling.
const float GYRO_SCALE = 131.0f;
const uint16_t GYRO_CALIBRATION_SAMPLES = 500;
const float GYRO_DEADBAND_DEG_S = 0.5f;
const unsigned long MPU_UPDATE_INTERVAL_US = 5000;
const unsigned long I2C_TIMEOUT_US = 3000;

// Closed-loop target tolerances and PID tuning.
const float DISTANCE_TOLERANCE_CM = 5.0f;
const float ANGLE_TOLERANCE_DEG = 4.0f;
const float ANGULAR_VELOCITY_TOLERANCE = 8.0f;
const uint8_t TARGET_STABLE_CYCLES = 5;
const int MIN_EFFECTIVE_PWM = 130;
const int MAX_PWM_STEP = 8;
const float DISTANCE_KP = 5.0f;
const float DISTANCE_KI = 0.0f;
const float DISTANCE_KD = 0.4f;
const float HEADING_KP = 3.0f;
const float HEADING_KI = 0.0f;
const float HEADING_KD = 0.15f;
const float TURN_KP = 3.0f;
const float TURN_KI = 0.0f;
const float TURN_KD = 0.2f;

// GPIO E-STOP, ultrasonic telemetry, and active braking.
const unsigned long ESTOP_CONFIRM_MS = 10;
const unsigned long ULTRASONIC_INTERVAL_MS = 50;
const unsigned long ULTRASONIC_TIMEOUT_US = 30000;
const unsigned long ULTRASONIC_WARNING_INTERVAL_MS = 5000;
const unsigned long ULTRASONIC_US_PER_CM = 58;
const uint8_t ACTIVE_BRAKE_PWM = 255;
const unsigned long ACTIVE_BRAKE_DURATION_MS = 200;

// Encoder and distance calibration.
const unsigned long ENCODER_DEBOUNCE_MS = 50;
const unsigned int COUNTS_PER_REVOLUTION = 4;
const float WHEEL_CIRCUMFERENCE_CM = 21.8f;
const float DISTANCE_PER_COUNT_CM =
    WHEEL_CIRCUMFERENCE_CM / COUNTS_PER_REVOLUTION;
const float LINEAR_DISTANCE_SCALE = 0.674f;

// Motion speed levels and distance synchronization.
const uint8_t MOVE_SPEED_LEVEL_PWM[2] = {200, 255};
const uint8_t TURN_SPEED_LEVEL_PWM[2] = {200, 255};
const uint8_t DISTANCE_START_BOOST_PWM = 200;
const unsigned long DISTANCE_START_BOOST_MS = 150;
const unsigned long DISTANCE_STALL_TIMEOUT_MS = 3000;
const uint8_t DISTANCE_SYNC_PWM_PER_COUNT = 5;
const uint8_t DISTANCE_SYNC_MAX_CORRECTION = 25;
const uint8_t DISTANCE_SYNC_MIN_PWM = 40;
