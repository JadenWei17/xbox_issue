"""Non-blocking UDP receiver that retains only the latest valid command."""

from __future__ import annotations

import json
import math
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ControlInput:
    x: float
    y: float
    left_stick_pressed: bool
    received_at: float


@dataclass(frozen=True)
class ReceiverStats:
    packets: int
    valid_packets: int
    invalid_packets: int
    latest_sender: tuple[str, int] | None


class UDPReceiver:
    def __init__(self, host: str, port: int, max_packet_size: int = 2048) -> None:
        self._address = (host, port)
        self._max_packet_size = max_packet_size
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest: ControlInput | None = None
        self._safety_commands: deque[str] = deque()
        self._packets = 0
        self._valid_packets = 0
        self._invalid_packets = 0
        self._latest_sender: tuple[str, int] | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self._address)
        sock.settimeout(0.2)
        self._socket = sock
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()

    def latest(self) -> ControlInput | None:
        with self._lock:
            return self._latest

    def pop_safety_commands(self) -> list[str]:
        with self._lock:
            commands = list(self._safety_commands)
            self._safety_commands.clear()
            return commands

    def stats(self) -> ReceiverStats:
        with self._lock:
            return ReceiverStats(
                packets=self._packets,
                valid_packets=self._valid_packets,
                invalid_packets=self._invalid_packets,
                latest_sender=self._latest_sender,
            )

    def close(self) -> None:
        self._stop_event.set()
        if self._socket is not None:
            self._socket.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._socket = None
        self._thread = None

    def _receive_loop(self) -> None:
        assert self._socket is not None
        while not self._stop_event.is_set():
            try:
                packet, sender = self._socket.recvfrom(self._max_packet_size)
            except socket.timeout:
                continue
            except OSError:
                if self._stop_event.is_set():
                    break
                raise
            command = self._parse_packet(packet)
            with self._lock:
                self._packets += 1
                self._latest_sender = sender
                if isinstance(command, ControlInput):
                    self._valid_packets += 1
                    self._latest = command
                elif command in ("ESTOP", "RESET"):
                    self._valid_packets += 1
                    self._safety_commands.append(command)
                else:
                    self._invalid_packets += 1

    @staticmethod
    def _parse_packet(packet: bytes) -> ControlInput | str | None:
        try:
            data: Any = json.loads(packet.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        if set(data) == {"command"} and data["command"] in ("ESTOP", "RESET"):
            return data["command"]
        x, y, pressed = data.get("x"), data.get("y"), data.get("left_stick_pressed")
        if isinstance(x, bool) or isinstance(y, bool):
            return None
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        if not isinstance(pressed, bool):
            return None
        x, y = float(x), float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        if not -1.0 <= x <= 1.0 or not -1.0 <= y <= 1.0:
            return None
        return ControlInput(x, y, pressed, time.monotonic())

    def __enter__(self) -> "UDPReceiver":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
