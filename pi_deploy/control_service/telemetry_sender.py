"""Send non-critical Arduino status telemetry to the Windows frontend."""

from __future__ import annotations

import json
import socket
import time
from typing import Any


class TelemetrySender:
    def __init__(self, host: str, port: int) -> None:
        self._target = (host, port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def publish_state(self, line: str) -> None:
        if not line.startswith("STATE,"):
            return
        state: dict[str, Any] = {"received_at": time.time()}
        for item in line.split(",")[1:]:
            key, separator, raw_value = item.partition("=")
            if not separator:
                continue
            if raw_value == "NA":
                value: Any = None
            elif key == "MODE":
                value = raw_value
            else:
                try:
                    value = float(raw_value) if "." in raw_value else int(raw_value)
                except ValueError:
                    value = raw_value
            state[key.lower()] = value
        payload = json.dumps(state, separators=(",", ":")).encode("utf-8")
        try:
            self._socket.sendto(payload, self._target)
        except OSError:
            # Telemetry must never interrupt motor control.
            pass

    def close(self) -> None:
        self._socket.close()
