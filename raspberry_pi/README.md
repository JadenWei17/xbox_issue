# Raspberry Pi robot controller

This program receives the newest Xbox left-stick state over UDP, smooths it,
mixes it for differential drive, and sends wheel speeds to an Arduino over USB.
If valid packets stop for 0.5 seconds, both motors are stopped automatically.

## Directory responsibilities

- `main.py` and the existing control modules implement Xbox UDP reception,
  GPIO E-STOP, Arduino serial communication, and drive control.
- `video/` is the independent libcamera H.264/RTP publishing service.
- `scripts/` starts or stops video without stopping robot control.
- `service_manager.py` can optionally supervise control and video as separate
  child processes.
- `VIDEO_README.md` contains complete camera, Windows receiver, WebRTC, and
  troubleshooting instructions.

The Windows RTP/OpenCV receiver, MediaMTX gateway, and browser service are
stored separately in `../windows_video_client/`. The Raspberry Pi video module
does not import or modify the control modules in this directory.

## Install and configure

Requires Python 3.10 or newer. On the Raspberry Pi:

```bash
cd raspberry_pi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyserial RPi.GPIO
```

`SERIAL_PORT` defaults to `"auto"`: one `/dev/ttyACM*` or `/dev/ttyUSB*`
device is selected automatically. If several are connected, set an explicit
device in `config.py`. Find the Arduino device with:

```bash
ls -l /dev/serial/by-id/ /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

A `/dev/serial/by-id/...` path is preferred because it remains stable across
reboots. The user may also need serial permission:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in after changing the group. UDP uses port 5000 on all Pi
interfaces; the Windows sender's `RASPBERRY_PI_IP` must be the Pi's address.

Connect Raspberry Pi GPIO17 to Arduino Mega D18 and connect both grounds.
GPIO17 is HIGH while motion is enabled and LOW while E-STOP is latched.

## Run

Connect the Arduino by USB, then run:

```bash
source .venv/bin/activate
python main.py
```

Ctrl+C and unexpected errors both trigger a final zero-speed command.
Once per second, a `[STATUS]` line reports UDP packet counts and source, latest
joystick values, mixed wheel speeds, timeout state, and serial write counts.

## UDP protocol

One UTF-8 JSON object per datagram:

```json
{"x":0.75,"y":-0.2}
```

`x` is forward/back and `y` is right/left, both finite numbers in `[-1, 1]`.
No additional fields are accepted. Invalid packets are ignored. Only the newest
valid packet is used.

Y and X button press edges send separate `{"command":"ESTOP"}` and
`{"command":"RESET"}` datagrams. E-STOP disables motion forwarding until a
RESET is received.

Distance mode sends a structured command:

```json
{"command":"MOVE","direction":"FWD","speed_level":2,"distance_cm":10}
```

`direction` is `FWD` or `BWD`, `speed_level` is 1, 2, or 3, and
`distance_cm` is an integer from 1 to 1000. While a distance move is active,
the Pi does not send manual timeout commands that could cancel the Arduino
task. A newer manual control packet, E-STOP, or RESET cancels the task.

## Arduino serial protocol

ASCII lines at 115200 baud:

```text
L:128,R:-64
```

`L` and `R` are signed integers from -255 to 255. Positive means forward,
negative means reverse, and zero means stop. The Arduino sketch must parse a
newline-terminated line in this format and refresh its own watchdog on receipt.
The additional `RESET` line is used only to clear the Arduino E-STOP latch.
Distance commands are forwarded without changing their values:

```text
MOVE FWD 2 10
MOVE BWD 3 7
```

The Arduino returns `DONE` after both encoder targets have been reached.
It first returns `ACK MOVE`; if no acknowledgement arrives within one second,
the Pi cancels the distance state and sends a stop command. `ERR COMMAND`,
`ERR ESTOP`, and `WATCHDOG` are printed as diagnostics.

## Test procedure

1. Lift the drive wheels off the floor and connect the Arduino.
2. Start `main.py`; confirm the UDP and Arduino messages appear.
3. Start `windows_controller/main.py` on Windows and move the left stick slowly.
4. Check forward, reverse, left/right turns, and that both wheels stop after the
   Windows process is closed or Wi-Fi is disconnected.
5. Press Ctrl+C on the Pi and confirm the motors stop.

To test without a controller, send one packet from another terminal:

```bash
python3 -c "import socket; socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b'{\"x\":0.3,\"y\":0}',('127.0.0.1',5000))"
```

Hardware-independent component tests can be run with:

```bash
python -m unittest -v test_components.py
```
