"""GPIO output for the independent Arduino E-STOP signal."""

from __future__ import annotations

import RPi.GPIO as GPIO


class EstopGPIO:
    def __init__(self, pin: int) -> None:
        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)

    def assert_estop(self) -> None:
        GPIO.output(self.pin, GPIO.LOW)

    def reset(self) -> None:
        GPIO.output(self.pin, GPIO.HIGH)

    def close(self) -> None:
        # Fail safe when the controller process exits.
        GPIO.output(self.pin, GPIO.LOW)
        GPIO.cleanup(self.pin)
