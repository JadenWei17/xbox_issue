# Arduino motor controller

This sketch targets an Arduino Mega 2560 with an Adafruit Motor Shield V1. It drives
the shield's 74HC595 direction register and PWM pins directly, so no
third-party library is required. Open `arduino.ino` in the Arduino
IDE, select the board and serial port, then upload.

Motor allocation:

- M3: front-left wheel
- M4: rear-left wheel
- M2: front-right wheel
- M1: rear-right wheel

The physical installation directions are currently unknown, so all four
reversal flags start as `false`. Send a low positive speed during a safe,
wheels-off-the-ground test. If a wheel turns backward, change its corresponding
entry in `MOTOR_REVERSED` (ordered M1, M2, M3, M4) to `true`.

The sketch accepts newline-terminated commands at 115200 baud:

```text
L:128,R:-64
```

Each value must be between -255 and 255. Invalid commands are ignored. If no
valid command arrives for 500 ms, all four motors are released automatically.
Arduino replies with `READY` after startup and sends a non-blocking status line
once per second: `OK L:...,R:...` while active or `STOP L:0,R:0` after timeout.

Mega D18 is the E-STOP input and must be connected to Raspberry Pi GPIO17 with
a common ground. A falling edge latches E-STOP; motor commands are ignored
until the Arduino receives `RESET` followed by a newline over USB serial.
