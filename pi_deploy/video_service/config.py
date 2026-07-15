"""Configuration for the Raspberry Pi rpicam-vid UDP publisher."""

from __future__ import annotations

import os


def _integer(
    name: str, default: int, minimum: int = 1, maximum: int | None = None
) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
# Change this one constant when a different capture frame rate is required.
CAMERA_FPS = 30
VIDEO_BITRATE = _integer("VIDEO_BITRATE", 1_000_000)
GOP_SIZE = _integer("GOP_SIZE", 15)
# There is intentionally only one output. The former AI/direct port was removed.
VIDEO_TARGET_IP = os.getenv("VIDEO_TARGET_IP", "100.67.201.122")
VIDEO_TARGET_PORT = _integer("VIDEO_TARGET_PORT", 5600, maximum=65_535)
UDP_PACKET_SIZE = _integer("UDP_PACKET_SIZE", 1316, maximum=65_507)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
