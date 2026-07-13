# Windows Xbox controller

The program starts in `MANUAL_MODE`. The original 30 Hz left-stick UDP control
is unchanged in this mode. Y sends E-STOP and X sends RESET in every mode.

- D-pad Up selects `MANUAL_MODE`.
- D-pad Right selects `DISTANCE_MODE`.

A zero joystick command is sent before every actual mode change. In distance
mode, periodic joystick packets stop and the terminal accepts:

```text
w 2 10
s 3 7
```

`w` means forward and `s` means backward. Speed levels 1, 2, and 3 correspond
to low, medium, and high speed. Distance is an integer number of centimetres
from 1 to 1000. Terminal input runs on a background thread so D-pad, Y, and X
remain responsive while waiting for a command.
