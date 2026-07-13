"""Runtime configuration for the Raspberry Pi controller."""

# UDP listener. 0.0.0.0 listens on every network interface.
UDP_HOST = "0.0.0.0"
UDP_PORT = 5000
UDP_MAX_PACKET_SIZE = 2048

# Hardware E-STOP output (BCM numbering): GPIO17 -> Arduino Mega D18.
ESTOP_GPIO_PIN = 17

# USB serial connection to Arduino. Use "auto" to discover ttyACM/ttyUSB ports,
# or set an explicit path such as "/dev/ttyACM0" or "/dev/serial/by-id/...".
SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUDRATE = 115200
SERIAL_WRITE_TIMEOUT_SECONDS = 0.1
# Opening an Arduino Uno USB serial port resets the board. Wait for its
# bootloader and sketch startup before sending the 30 Hz command stream.
SERIAL_STARTUP_DELAY_SECONDS = 2.0

# Main control loop and fail-safe timeout.
CONTROL_RATE_HZ = 30.0
CONTROL_TIMEOUT_SECONDS = 0.5
STATUS_INTERVAL_SECONDS = 1.0

# Input shaping. ALPHA is the share of the newest sample in an EMA.
INPUT_DEADZONE = 0.03
FILTER_ALPHA = 0.35

# Differential-drive output range and optional per-wheel calibration.
MAX_MOTOR_SPEED = 255
LEFT_SPEED_SCALE = 1.0
RIGHT_SPEED_SCALE = 1.0
# Lower values make steering gentler and increase the turning radius.
TURN_SCALE = 0.5

# Arduino line protocol: L:<signed integer>,R:<signed integer>\n
SERIAL_COMMAND_FORMAT = "L:{left},R:{right}\n"
SERIAL_RESET_COMMAND = "RESET\n"
