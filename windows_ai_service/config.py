"""Environment-based configuration for the independent AI service."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _integer(name: str, default: int, minimum: int = 1, maximum: int = 65_535) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _float(name: str, default: float, minimum: float, maximum: float) -> float:
    value = float(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


MODEL_PATH = Path(
    os.getenv("YOLO_MODEL_PATH", str(PROJECT_ROOT / "models" / "cat_detector" / "best.pt"))
).expanduser().resolve()
WHEP_URL = os.getenv("AI_WHEP_URL", "http://127.0.0.1:8889/robot/whep")
AI_HOST = os.getenv("AI_HOST", "127.0.0.1")
AI_PORT = _integer("AI_PORT", 8091)
CONFIDENCE = _float("AI_CONFIDENCE", 0.60, 0.0, 1.0)
IOU = _float("AI_IOU", 0.70, 0.0, 1.0)
IMAGE_SIZE = _integer("AI_IMAGE_SIZE", 640, maximum=4096)
MAX_FPS = _float("AI_MAX_FPS", 10.0, 0.1, 120.0)
DEVICE = os.getenv("AI_DEVICE", "0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
