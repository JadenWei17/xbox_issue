"""Publish one low-latency H.264/MPEG-TS stream with rpicam-vid over UDP."""

from __future__ import annotations

import logging
import shutil
import signal
import subprocess
import threading

import config

LOGGER = logging.getLogger(__name__)


def build_command() -> list[str]:
    executable = shutil.which("rpicam-vid")
    if executable is None:
        raise RuntimeError("rpicam-vid is not installed or not in PATH")

    output = (
        f"udp://{config.VIDEO_TARGET_IP}:{config.VIDEO_TARGET_PORT}"
        f"?pkt_size={config.UDP_PACKET_SIZE}"
    )
    return [
        executable,
        "--timeout", "0",
        "--nopreview",
        "--width", str(config.CAMERA_WIDTH),
        "--height", str(config.CAMERA_HEIGHT),
        "--framerate", str(config.CAMERA_FPS),
        "--codec", "libav",
        # Pi 5 otherwise emits B-frames, which WebRTC cannot carry.
        "--low-latency",
        "--libav-format", "mpegts",
        "--bitrate", str(config.VIDEO_BITRATE),
        "--intra", str(config.GOP_SIZE),
        "--output", output,
    ]


class UDPStreamer:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()
        if self._process is not None and self._process.poll() is None:
            self._process.send_signal(signal.SIGINT)

    def run(self) -> int:
        try:
            command = build_command()
            LOGGER.info(
                "Starting rpicam-vid: %dx%d @ %d FPS, H.264 %d bps, GOP %d",
                config.CAMERA_WIDTH, config.CAMERA_HEIGHT, config.CAMERA_FPS,
                config.VIDEO_BITRATE, config.GOP_SIZE,
            )
            LOGGER.info(
                "Single MPEG-TS/UDP target: udp://%s:%d",
                config.VIDEO_TARGET_IP, config.VIDEO_TARGET_PORT,
            )
            self._process = subprocess.Popen(command)
            while not self._stop_event.wait(0.25):
                return_code = self._process.poll()
                if return_code is not None:
                    if return_code != 0:
                        LOGGER.error("rpicam-vid exited with code %d", return_code)
                    return return_code
            return 0
        except (OSError, RuntimeError, ValueError) as error:
            LOGGER.error("Video startup failed: %s", error)
            return 1
        finally:
            process = self._process
            if process is not None and process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            self._process = None
            LOGGER.info("Camera and UDP resources released")


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    streamer = UDPStreamer()
    signal.signal(signal.SIGTERM, lambda *_: streamer.stop())
    signal.signal(signal.SIGINT, lambda *_: streamer.stop())
    raise SystemExit(streamer.run())


if __name__ == "__main__":
    main()
