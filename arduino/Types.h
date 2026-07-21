#pragma once

#include <Arduino.h>

enum RobotState {
  IDLE,
  MANUAL,
  DISTANCE_MOVE,
  TURN_IN_PLACE,
  ESTOP
};

enum EstopSource {
  ESTOP_SOURCE_NONE,
  ESTOP_SOURCE_GPIO17
};

enum UltrasonicPhase {
  ULTRASONIC_IDLE,
  ULTRASONIC_TRIGGER_HIGH,
  ULTRASONIC_WAIT_RISE,
  ULTRASONIC_WAIT_FALL
};

class PIDController {
 public:
  void configure(float p, float i, float d, float outputMin,
                 float outputMax, float integralMin, float integralMax) {
    kp = p;
    ki = i;
    kd = d;
    outMin = outputMin;
    outMax = outputMax;
    intMin = integralMin;
    intMax = integralMax;
    reset();
  }

  void reset() {
    integral = 0;
    previous = 0;
    hasPrevious = false;
  }

  float update(float error, float dt) {
    if (!(dt > 0.00001f && dt < 0.5f)) {
      return 0;
    }
    integral = constrain(integral + error * dt, intMin, intMax);
    float derivative = hasPrevious ? (error - previous) / dt : 0;
    previous = error;
    hasPrevious = true;
    return constrain(kp * error + ki * integral + kd * derivative,
                     outMin, outMax);
  }

 private:
  float kp;
  float ki;
  float kd;
  float outMin;
  float outMax;
  float intMin;
  float intMax;
  float integral;
  float previous;
  bool hasPrevious;
};

struct RobotPose {
  float xCm;
  float yCm;
  float headingDeg;
  float headingTotalDeg;
  float leftDistanceCm;
  float rightDistanceCm;
  float linearVelocityCmS;
  float angularVelocityDegS;
};
