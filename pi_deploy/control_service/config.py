"""Runtime configuration for the Raspberry Pi controller."""

# UDP listener. 0.0.0.0 listens on every network interface.
UDP_HOST = "0.0.0.0"
UDP_PORT = 5000
UDP_MAX_PACKET_SIZE = 2048

# Non-critical status output for the Windows frontend. Motor control never
# waits for this UDP channel and continues normally when the frontend is off.
TELEMETRY_TARGET_IP = "100.67.201.122"
TELEMETRY_TARGET_PORT = 5010

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
MOVE_ACK_TIMEOUT_SECONDS = 1.0
MAX_DISTANCE_CM = 1000
VALID_SPEED_LEVELS = (1, 2)

# Input shaping. ALPHA is the share of the newest sample in an EMA.
INPUT_DEADZONE = 0.03
FILTER_ALPHA = 0.35

# Differential-drive output range and optional per-wheel calibration.
MAX_MOTOR_SPEED = 255
# Manual joystick commands remain zero in the deadzone. Every non-zero wheel
# command is raised to this floor to overcome drivetrain breakaway torque.
MANUAL_MIN_MOTOR_SPEED = 155
LEFT_SPEED_SCALE = 1.0
RIGHT_SPEED_SCALE = 1.0
# Lower values make steering gentler and increase the turning radius.
TURN_SCALE = 0.5

# Arduino line protocol: L:<signed integer>,R:<signed integer>\n
SERIAL_COMMAND_FORMAT = "L:{left},R:{right}\n"
SERIAL_RESET_COMMAND = "RESET\n"
SERIAL_IDLE_COMMAND = "IDLE\n"
SERIAL_MOVE_COMMAND_FORMAT = "MOVE,{direction},{speed_level},{distance_cm:.1f}\n"
SERIAL_TURN_COMMAND_FORMAT = "TURN,{direction},{speed_level},{angle_deg:.1f}\n"
SERIAL_AVOIDANCE_ON_COMMAND = "AVOID,ON\n"
SERIAL_AVOIDANCE_OFF_COMMAND = "AVOID,OFF\n"

# Keyboard forward-distance obstacle avoidance. The front ultrasonic sensor is
# not useful while reversing, so reverse commands retain their existing path.
AVOIDANCE_SLOW_DISTANCE_CM = 50.0
AVOIDANCE_STOP_DISTANCE_CM = 30.0
# Arduino considers an error of 5 cm already complete, so a 5 cm MOVE would
# finish without starting the motors. Keep avoidance segments above that limit.
AVOIDANCE_FAST_CHUNK_CM = 10.0
AVOIDANCE_SLOW_CHUNK_CM = 10.0
AVOIDANCE_BYPASS_DISTANCE_CM = 50.0
AVOIDANCE_TURN_SPEED_LEVEL = 1
AVOIDANCE_BYPASS_SPEED_LEVEL = 1
AVOIDANCE_SENSOR_SETTLE_SECONDS = 0.4
