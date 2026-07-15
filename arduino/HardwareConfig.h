#pragma once

#include <Arduino.h>

// Sensors and safety input.
const uint8_t MPU_ADDRESS = 0x68;
const uint8_t ESTOP_PIN = 18;
const uint8_t LEFT_ENCODER_PIN = 2;
const uint8_t RIGHT_ENCODER_PIN = 19;
const uint8_t ULTRASONIC_TRIG_PIN = 22;
const uint8_t ULTRASONIC_ECHO_PIN = 23;

// Adafruit Motor Shield V1 74HC595 control pins.
const uint8_t MOTOR_LATCH_PIN = 12;
const uint8_t MOTOR_CLOCK_PIN = 4;
const uint8_t MOTOR_ENABLE_PIN = 7;
const uint8_t MOTOR_DATA_PIN = 8;
const uint8_t MOTOR_PWM_PINS[4] = {11, 3, 6, 5};
const uint8_t MOTOR_A_BITS[4] = {2, 1, 5, 0};
const uint8_t MOTOR_B_BITS[4] = {3, 4, 7, 6};

// Set an entry true when that physical motor is mounted in reverse.
// Array order: M1, M2, M3, M4.
const bool MOTOR_REVERSED[4] = {false, false, false, false};
const size_t MOTOR_M1 = 0;
const size_t MOTOR_M2 = 1;
const size_t MOTOR_M3 = 2;
const size_t MOTOR_M4 = 3;
