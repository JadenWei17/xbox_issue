"""Configuration for the Windows controller program."""

# Change this to the Raspberry Pi's IP address on your local network.
RASPBERRY_PI_IP = "100.96.200.113"
RASPBERRY_PI_PORT = 5000

# Controller sampling and UDP transmission frequency.
SEND_RATE_HZ = 30.0
SEND_INTERVAL_SECONDS = 1.0 / SEND_RATE_HZ
LEFT_STICK_DEADZONE = 0.08

# Distance-mode command limits.
MIN_DISTANCE_CM = 1
MAX_DISTANCE_CM = 1000
VALID_SPEED_LEVELS = (1, 2, 3)
