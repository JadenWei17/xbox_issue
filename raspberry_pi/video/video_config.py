"""Central configuration for Raspberry Pi camera and RTP publishing."""

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


CAMERA_WIDTH = _integer("CAMERA_WIDTH", 1280)
CAMERA_HEIGHT = _integer("CAMERA_HEIGHT", 720)
CAMERA_FPS = _integer("CAMERA_FPS", 30)
VIDEO_BITRATE = _integer("VIDEO_BITRATE", 2_000_000)

RTP_TARGET_IP = os.getenv("RTP_TARGET_IP", "100.67.201.122")
RTP_TARGET_PORT = _integer("RTP_TARGET_PORT", 5004, maximum=65_535)
RTP_PAYLOAD_TYPE = _integer("RTP_PAYLOAD_TYPE", 96, minimum=96, maximum=127)
GOP_SIZE = _integer("GOP_SIZE", 15)

# A second RTP copy feeds MediaMTX on Windows. It defaults to the same Windows
# LAN/Tailscale address, but uses a separate port so AI and WebRTC receivers do
# not compete for one unicast UDP socket.
WEBRTC_TARGET_IP = os.getenv("WEBRTC_TARGET_IP", RTP_TARGET_IP)
WEBRTC_TARGET_PORT = _integer("WEBRTC_TARGET_PORT", 5600, maximum=65_535)

GST_QUEUE_BUFFERS = _integer("GST_QUEUE_BUFFERS", 2)
GST_UDP_BUFFER_SIZE = _integer("GST_UDP_BUFFER_SIZE", 131_072)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
