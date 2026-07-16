"""Thread-safe latest-result storage shared by inference and HTTP threads."""

from __future__ import annotations

import threading
import time
from copy import deepcopy


class DetectionState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, object] = {
            "online": False,
            "stream": False,
            "model": None,
            "device": None,
            "width": 0,
            "height": 0,
            "detections": [],
            "updated_at": None,
            "error": "AI service is starting",
        }

    def update(self, **values: object) -> None:
        with self._lock:
            self._data.update(values)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            data = deepcopy(self._data)
        updated_at = data.get("updated_at")
        data["stale"] = not isinstance(updated_at, (int, float)) or time.time() - updated_at > 3.0
        data["online"] = bool(data["stream"] and not data["stale"] and not data["error"])
        return data


state = DetectionState()
