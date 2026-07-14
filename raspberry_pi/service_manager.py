"""Optionally supervise isolated Raspberry Pi control and RTP video processes."""

from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)
RASPBERRY_PI_DIR = Path(__file__).resolve().parent


@dataclass
class Service:
    name: str
    command: list[str]
    process: subprocess.Popen[str] | None = None
    restart_at: float = 0.0

    def start(self) -> None:
        self.process = subprocess.Popen(
            self.command, cwd=RASPBERRY_PI_DIR, text=True
        )
        LOGGER.info("%s started (PID %d)", self.name, self.process.pid)

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        LOGGER.info("Stopping %s", self.name)
        self.process.send_signal(signal.SIGINT)
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-control",
        action="store_true",
        help="also start the existing main.py control process",
    )
    parser.add_argument(
        "--no-restart", action="store_true", help="do not restart failed services"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s supervisor: %(message)s",
    )
    services = [
        Service("video_stream", [sys.executable, "-m", "video.rtp_streamer"]),
    ]
    if args.with_control:
        services.insert(
            0,
            Service(
                "robot_control",
                [sys.executable, str(RASPBERRY_PI_DIR / "main.py")],
            ),
        )

    stopping = False

    def request_stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        for service in services:
            service.start()
        while not stopping:
            now = time.monotonic()
            for service in services:
                process = service.process
                if process is None:
                    if not args.no_restart and service.restart_at and now >= service.restart_at:
                        service.restart_at = 0.0
                        try:
                            service.start()
                        except OSError as error:
                            LOGGER.error("Could not restart %s: %s", service.name, error)
                            service.restart_at = now + 5.0
                    continue
                return_code = process.poll()
                if return_code is None:
                    continue
                LOGGER.error(
                    "%s exited with code %d; other services remain running",
                    service.name,
                    return_code,
                )
                service.process = None
                if args.no_restart:
                    continue
                if service.restart_at == 0.0:
                    service.restart_at = now + 2.0
                    LOGGER.info("%s will restart in 2 seconds", service.name)
            time.sleep(0.25)
    finally:
        for service in reversed(services):
            service.stop()
        LOGGER.info("All supervisor-owned child processes stopped")


if __name__ == "__main__":
    main()
