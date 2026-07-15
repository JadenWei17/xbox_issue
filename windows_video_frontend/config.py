"""Configuration for the independent browser frontend."""

from __future__ import annotations

import os


def _integer(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not 1 <= value <= 65_535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return value


CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
# Robot start/stop endpoints must not be exposed to the LAN by default.
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = _integer("WEB_PORT", 8080)
MEDIAMTX_HOST = os.getenv("MEDIAMTX_HOST", "")
MEDIAMTX_WEBRTC_PORT = _integer("MEDIAMTX_WEBRTC_PORT", 8889)
MEDIAMTX_PATH = os.getenv("MEDIAMTX_PATH", "robot")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
PI_SSH_TARGET = os.getenv("PI_SSH_TARGET", "sws3009b2@100.96.200.113")
SSH_CONNECT_TIMEOUT_SECONDS = _integer("SSH_CONNECT_TIMEOUT_SECONDS", 5)
TELEMETRY_LISTEN_HOST = os.getenv("TELEMETRY_LISTEN_HOST", "0.0.0.0")
TELEMETRY_LISTEN_PORT = _integer("TELEMETRY_LISTEN_PORT", 5010)
