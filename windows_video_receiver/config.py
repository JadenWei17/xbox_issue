"""Configuration for the independent MediaMTX receiver service."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _integer(name: str, default: int, minimum: int = 1, maximum: int = 65_535) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


VIDEO_LISTEN_HOST = os.getenv("VIDEO_LISTEN_HOST", "0.0.0.0")
VIDEO_UDP_PORT = _integer("VIDEO_UDP_PORT", 5600)
MEDIAMTX_WEBRTC_PORT = _integer("MEDIAMTX_WEBRTC_PORT", 8889)
MEDIAMTX_ICE_PORT = _integer("MEDIAMTX_ICE_PORT", 8189)
MEDIAMTX_PATH = os.getenv("MEDIAMTX_PATH", "robot")
MEDIAMTX_BINARY = Path(
    os.getenv("MEDIAMTX_BINARY", str(PROJECT_ROOT / "mediamtx.exe"))
).expanduser().resolve()
