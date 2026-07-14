"""Configuration for the Windows WebRTC gateway and browser viewer."""

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
RTP_PAYLOAD_TYPE = _integer("RTP_PAYLOAD_TYPE", 96, minimum=96, maximum=127)

RTP_LISTEN_HOST = os.getenv("RTP_LISTEN_HOST", "0.0.0.0")
WEBRTC_RTP_PORT = _integer("WEBRTC_RTP_PORT", 5600, maximum=65_535)
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = _integer("WEB_PORT", 8080, maximum=65_535)
MEDIAMTX_WEBRTC_PORT = _integer(
    "MEDIAMTX_WEBRTC_PORT", 8889, maximum=65_535
)
MEDIAMTX_ICE_PORT = _integer("MEDIAMTX_ICE_PORT", 8189, maximum=65_535)
MEDIAMTX_PATH = os.getenv("MEDIAMTX_PATH", "robot")
MEDIAMTX_BINARY = os.getenv("MEDIAMTX_BINARY", "mediamtx.exe")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
