"""Non-blocking terminal input for distance-mode commands."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

from config import MAX_DISTANCE_CM, MIN_DISTANCE_CM, VALID_SPEED_LEVELS


@dataclass(frozen=True)
class DistanceCommand:
    direction: str
    speed_level: int
    distance_cm: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "command": "MOVE",
            "direction": self.direction,
            "speed_level": self.speed_level,
            "distance_cm": self.distance_cm,
        }


def parse_distance_command(text: str) -> DistanceCommand:
    parts = text.strip().lower().split()
    if len(parts) != 3 or parts[0] not in ("w", "s"):
        raise ValueError("use: w <speed_level> <distance_cm> or s ...")
    try:
        speed_level = int(parts[1])
        distance_cm = int(parts[2])
    except ValueError as error:
        raise ValueError("speed_level and distance_cm must be integers") from error
    if speed_level not in VALID_SPEED_LEVELS:
        raise ValueError(f"speed_level must be one of {VALID_SPEED_LEVELS}")
    if not MIN_DISTANCE_CM <= distance_cm <= MAX_DISTANCE_CM:
        raise ValueError(
            f"distance_cm must be in [{MIN_DISTANCE_CM}, {MAX_DISTANCE_CM}]"
        )
    return DistanceCommand(
        direction="FWD" if parts[0] == "w" else "BWD",
        speed_level=speed_level,
        distance_cm=distance_cm,
    )


class KeyboardInput:
    def __init__(self) -> None:
        self._lines: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def pop_lines(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(self._lines.get_nowait())
            except queue.Empty:
                return lines

    def _read_loop(self) -> None:
        while True:
            try:
                line = input()
            except EOFError:
                return
            self._lines.put(line)
