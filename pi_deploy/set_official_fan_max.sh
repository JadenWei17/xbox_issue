#!/bin/sh
set -eu

CONFIG=/boot/firmware/config.txt
BACKUP=/boot/firmware/config.txt.before-fan-max
START_MARKER="# ROBOT FAN MAX START"
END_MARKER="# ROBOT FAN MAX END"

if [ ! -f "$CONFIG" ]; then
    echo "Expected Raspberry Pi boot configuration at $CONFIG" >&2
    exit 1
fi

if [ ! -f "$BACKUP" ]; then
    cp "$CONFIG" "$BACKUP"
fi

sed -i "/$START_MARKER/,/$END_MARKER/d" "$CONFIG"
cat >>"$CONFIG" <<'EOF'

# ROBOT FAN MAX START
# Official Raspberry Pi 5 fan: always run at 100% after kernel startup.
dtparam=fan_temp0=0
dtparam=fan_temp0_hyst=0
dtparam=fan_temp0_speed=255
dtparam=fan_temp1_speed=255
dtparam=fan_temp2_speed=255
dtparam=fan_temp3_speed=255
# ROBOT FAN MAX END
EOF

echo "Official fan maximum-speed configuration installed."
echo "Reboot the Raspberry Pi to apply it: sudo reboot"
