# Arduino motor controller

This sketch targets an Arduino Mega 2560 with an Adafruit Motor Shield V1. It drives
the shield's 74HC595 direction register and PWM pins directly, so no
third-party library is required. Open `arduino.ino` in the Arduino
IDE, select the board and serial port, then upload.

Motor allocation:

- M1: front-left wheel
- M2: rear-left wheel
- M4: front-right wheel
- M3: rear-right wheel

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
The input must remain LOW for 10 ms before the latch is accepted, filtering
short motor-start EMI spikes without adding blocking delays. RESET is rejected
while D18 is still LOW.

## Local ultrasonic E-STOP

An HC-SR04 at the front of the robot is sampled by a non-blocking `micros()`
state machine every 50 ms. It does not use `delay()`, `pulseIn()`, or an ISR.
The ultrasonic E-STOP is armed only when the robot has positive forward motion:
MANUAL left/right speed sum greater than zero, or a forward DISTANCE_MOVE.
Stationary, reverse, and in-place turns do not accumulate obstacle confirmations.

Two consecutive valid readings below 30 cm enter the existing ESTOP state,
stop all four motors locally, cancel any distance task, and report:

```text
ESTOP source=ULTRASONIC distance_cm=12
```

Both GPIO17 and ultrasonic E-STOP use 200 ms of non-blocking L293D dynamic
braking before releasing the motors. During braking, both direction inputs are
LOW and each motor Enable/PWM is 255. Ordinary zero-speed commands and normal
distance completion continue to coast, avoiding continuous brake current.
`ACTIVE_BRAKE_PWM` and `ACTIVE_BRAKE_DURATION_MS` are centralized constants.

No echo, timeout, and zero-distance results are invalid rather than obstacles.
Warnings are limited to once per 5 seconds. GPIO17 and ultrasonic requests
share the same motor-stop and ESTOP state-transition function. X/RESET can
clear an ultrasonic E-STOP immediately; only a physically LOW D18 GPIO17
signal blocks reset.

## Distance moves and encoders

The original manual command remains supported. A second newline-terminated
command starts a non-blocking distance move:

```text
MOVE FWD 2 10
MOVE BWD 3 7
```

Direction is `FWD` or `BWD`; speed levels 1, 2, and 3 map to PWM values 85,
170, and 255. Distance is an integer from 1 to 1000 cm. The target encoder
count is rounded upward. With 4 counts per wheel revolution and a 21.8 cm wheel
circumference, one count represents 5.45 cm. The Arduino sends `DONE` when both
sides reach the target. Each side is stopped independently when it reaches the
target, preventing the faster side from travelling farther while waiting for
the slower side.

Every distance move starts with a non-blocking 150 ms PWM 200 boost when the
selected cruise PWM is lower, then returns to the configured 85/170/255 level.
If either encoder makes no progress for 3 seconds, all motors stop and Arduino
returns `ERR STALL LEFT`, `ERR STALL RIGHT`, or `ERR STALL BOTH`.

While both sides are moving, encoder-count feedback adjusts PWM to reduce the
left/right count error. Each count of lead changes the correction by 5 PWM,
limited to 25 PWM. The slower side is increased and the faster side decreased;
each side still stops independently at its own target count.

Serial diagnostics include `ACK MOVE` for an accepted distance command,
`ERR COMMAND` for invalid syntax, `ERR ESTOP` when E-STOP blocks a command, and
`WATCHDOG` when the 500 ms manual-command timeout stops the motors.
During a distance move, the once-per-second status includes left/right counts,
the common target, and current PWM, for example:

```text
MOVE C L:12,R:14,T:19 PWM L:85,R:85
```

The left open-drain Hall encoder connects to Mega D2 and the right encoder to
D19. Both use `INPUT_PULLUP` and a falling-edge interrupt with the same 50 ms
debounce rule as `Tachometer_Complete.ino`. D20 and D21 remain reserved for the
MPU6500 I2C connection.

State transitions are non-blocking:

```text
IDLE -- L:x,R:y --> MANUAL
IDLE/MANUAL -- MOVE --> DISTANCE_MOVE -- targets reached --> IDLE + DONE
any state -- E-STOP --> ESTOP -- RESET --> IDLE
```

An `L:x,R:y` command cancels a distance move. E-STOP always has priority. The
500 ms serial watchdog applies to MANUAL only; encoder-controlled moves do not
require repeated serial commands.

## Mega 2560 pin allocation

| Pin | Function |
| --- | --- |
| D2 | Left encoder input |
| D3 | M2 PWM |
| D4 | Motor Shield clock |
| D5 | M4 PWM |
| D6 | M3 PWM |
| D7 | Motor Shield enable |
| D8 | Motor Shield data |
| D11 | M1 PWM |
| D12 | Motor Shield latch |
| D18 | E-STOP input from Raspberry Pi GPIO17 |
| D19 | Right encoder input |
| D20/D21 | Reserved for MPU6500 I2C |
| D22 | HC-SR04 TRIG output |
| D23 | HC-SR04 ECHO input |
