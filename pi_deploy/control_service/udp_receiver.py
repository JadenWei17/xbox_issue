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
    received_at: float


@dataclass(frozen=True)
class DistanceMove:
    direction: str
    speed_level: int
    distance_cm: int
    received_at: float


@dataclass(frozen=True)
class TurnMove:
    direction: str
    speed_level: int
    angle_deg: int
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
        self._distance_moves: deque[DistanceMove] = deque()
        self._turn_moves: deque[TurnMove] = deque()
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

    def pop_distance_moves(self) -> list[DistanceMove]:
        with self._lock:
            commands = list(self._distance_moves)
            self._distance_moves.clear()
            return commands

    def pop_turn_moves(self) -> list[TurnMove]:
        with self._lock:
            commands = list(self._turn_moves)
            self._turn_moves.clear()
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
                elif command in ("ESTOP", "RESET", "IDLE"):
                    self._valid_packets += 1
                    self._safety_commands.append(command)
                elif isinstance(command, DistanceMove):
                    self._valid_packets += 1
                    self._distance_moves.append(command)
                elif isinstance(command, TurnMove):
                    self._valid_packets += 1
                    self._turn_moves.append(command)
                else:
                    self._invalid_packets += 1

    @staticmethod
    def _parse_packet(packet: bytes) -> ControlInput | DistanceMove | TurnMove | str | None:
        try:
            data: Any = json.loads(packet.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        if set(data) == {"command"} and data["command"] in ("ESTOP", "RESET", "IDLE"):
            return data["command"]
        if set(data) == {"command", "direction", "speed_level", "distance_cm"}:
            command = data["command"]
            direction = data["direction"]
            speed_level = data["speed_level"]
            distance_cm = data["distance_cm"]
            if command != "MOVE" or direction not in ("FWD", "BWD"):
                return None
            if not isinstance(speed_level, int) or isinstance(speed_level, bool):
                return None
            if speed_level not in (1, 2):
                return None
            if isinstance(distance_cm, bool) or not isinstance(distance_cm, int):
                return None
            if not 1 <= distance_cm <= 1000:
                return None
            return DistanceMove(
                direction, speed_level, distance_cm, time.monotonic()
            )
        if set(data) == {"command", "direction", "speed_level", "angle_deg"}:
            if data["command"] != "TURN" or data["direction"] not in ("LEFT", "RIGHT"):
                return None
            speed_level, angle_deg = data["speed_level"], data["angle_deg"]
            if isinstance(speed_level, bool) or not isinstance(speed_level, int) or speed_level not in (1, 2):
                return None
            if isinstance(angle_deg, bool) or not isinstance(angle_deg, int) or not 1 <= angle_deg <= 720:
                return None
            return TurnMove(data["direction"], speed_level, angle_deg, time.monotonic())
        if set(data) != {"x", "y"}:
            return None
        x, y = data["x"], data["y"]
        if isinstance(x, bool) or isinstance(y, bool):
            return None
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        x, y = float(x), float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        if not -1.0 <= x <= 1.0 or not -1.0 <= y <= 1.0:
            return None
        return ControlInput(x, y, time.monotonic())

    def __enter__(self) -> "UDPReceiver":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
