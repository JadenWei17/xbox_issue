"""Arduino USB serial output."""

from __future__ import annotations

import time
from collections import deque

import serial
from serial.tools import list_ports


def resolve_serial_port(configured_port: str) -> str:
    """Resolve an explicit port or select one unambiguous USB serial device."""
    if configured_port.lower() != "auto":
        return configured_port

    ports = list(list_ports.comports())
    usb_candidates = [
        port
        for port in ports
        if port.device.startswith(("/dev/ttyACM", "/dev/ttyUSB"))
    ]

    if len(usb_candidates) == 1:
        return usb_candidates[0].device

    if not usb_candidates:
        detected = ", ".join(port.device for port in ports) or "none"
        raise RuntimeError(
            "No Arduino USB serial port found. Detected serial ports: "
            f"{detected}. Check the USB data cable and run 'ls /dev/ttyACM* "
            "/dev/ttyUSB* 2>/dev/null'."
        )

    choices = ", ".join(
        f"{port.device} ({port.description})" for port in usb_candidates
    )
    raise RuntimeError(
        f"Multiple USB serial ports found: {choices}. Set SERIAL_PORT in "
        "config.py to the Arduino device explicitly."
    )


class SerialSender:
    def __init__(
        self,
        port: str,
        baudrate: int,
        write_timeout: float,
        command_format: str,
        startup_delay: float = 0.0,
    ) -> None:
        self.command_format = command_format
        self.port = resolve_serial_port(port)
        self.commands_sent = 0
        self.bytes_sent = 0
        self.last_command = "none"
        self.last_sent_at: float | None = None
        self.responses_received = 0
        self.last_response = "none"
        self._response_buffer = bytearray()
        self._responses: deque[str] = deque()
        self._serial = serial.Serial(
            port=self.port,
            baudrate=baudrate,
            timeout=0,
            write_timeout=write_timeout,
        )
        if startup_delay > 0:
            time.sleep(startup_delay)
        # Collect READY/status lines emitted while the Arduino was starting.
        self._read_responses()

    def send(self, left: int, right: int) -> None:
        command = self.command_format.format(left=left, right=right)
        self.send_raw(command)

    def send_raw(self, command: str) -> None:
        self._read_responses()
        payload = command.encode("ascii")
        written = self._serial.write(payload)
        if written != len(payload):
            raise serial.SerialTimeoutException(
                f"Only {written}/{len(payload)} serial bytes were written"
            )
        self.commands_sent += 1
        self.bytes_sent += written
        self.last_command = command.rstrip()
        self.last_sent_at = time.monotonic()

    def pop_responses(self) -> list[str]:
        self._read_responses()
        responses = list(self._responses)
        self._responses.clear()
        return responses

    def _read_responses(self) -> None:
        waiting = self._serial.in_waiting
        if waiting <= 0:
            return
        self._response_buffer.extend(self._serial.read(waiting))
        while b"\n" in self._response_buffer:
            raw_line, _, remainder = self._response_buffer.partition(b"\n")
            self._response_buffer = bytearray(remainder)
            line = raw_line.rstrip(b"\r").decode("ascii", errors="replace")
            if line:
                self.responses_received += 1
                self.last_response = line
                self._responses.append(line)

    def stop(self) -> None:
        self.send(0, 0)
        self._serial.flush()

    def close(self) -> None:
        self._serial.close()

    def __enter__(self) -> "SerialSender":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
