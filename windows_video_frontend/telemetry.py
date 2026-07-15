"""Receive the latest non-critical robot telemetry without queueing old data."""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any


class TelemetryReceiver:
    def __init__(self, host: str, port: int) -> None:
        self._address = (host, port)
        self._lock = threading.Lock()
        self._latest: dict[str, Any] | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self._address)
        while True:
            packet, _ = sock.recvfrom(4096)
            try:
                data = json.loads(packet.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                data["frontend_received_at"] = time.time()
                with self._lock:
                    self._latest = data

    def latest(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self._latest) if self._latest is not None else {}
        received = data.get("frontend_received_at")
        data["online"] = (
            isinstance(received, (int, float)) and time.time() - received < 2.0
        )
        return data
