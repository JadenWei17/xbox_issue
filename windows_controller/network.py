"""UDP client used to send controller states to the Raspberry Pi."""

from __future__ import annotations

import json
import socket
from typing import Any

from .config import RASPBERRY_PI_IP, RASPBERRY_PI_PORT


class RaspberryPiClient:
    def __init__(self, host: str = RASPBERRY_PI_IP, port: int = RASPBERRY_PI_PORT):
        self.host = host
        self.port = port
        self._address = (host, port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data: dict[str, Any]) -> None:
        """Send one controller state as a single UDP JSON datagram."""
        message = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self._socket.sendto(message, self._address)

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> "RaspberryPiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
