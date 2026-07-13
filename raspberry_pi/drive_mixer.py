"""Differential-drive mixing."""

from __future__ import annotations


def mix_drive(x: float, y: float, turn_scale: float = 1.0) -> tuple[float, float]:
    """Convert forward x and right-turn y into normalized wheel speeds."""
    steering = y * max(0.0, turn_scale)
    left = x + steering
    right = x - steering
    peak = max(1.0, abs(left), abs(right))
    return left / peak, right / peak


def scale_wheel_speeds(
    left: float,
    right: float,
    max_speed: int,
    left_scale: float = 1.0,
    right_scale: float = 1.0,
) -> tuple[int, int]:
    def scale(value: float, calibration: float) -> int:
        return round(max(-1.0, min(1.0, value * calibration)) * max_speed)

    return scale(left, left_scale), scale(right, right_scale)
