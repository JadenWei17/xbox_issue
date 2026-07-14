"""Run one libcamera capture and publish low-latency H.264/RTP outputs."""

from __future__ import annotations

import logging
import shlex
import signal
import subprocess
import threading
from collections.abc import Sequence

from . import video_config as config
from .camera_service import discover_camera_pipeline

LOGGER = logging.getLogger(__name__)


def build_pipeline() -> str:
    camera = discover_camera_pipeline()
    LOGGER.info("Selected encoder: %s", camera.encoder_name)
    queue = (
        f"queue max-size-buffers={config.GST_QUEUE_BUFFERS} "
        "max-size-bytes=0 max-size-time=0 leaky=downstream flush-on-eos=true"
    )
    parsed_stream = "h264parse config-interval=-1 ! tee name=h264"
    payloader = (
        f"rtph264pay pt={config.RTP_PAYLOAD_TYPE} config-interval=-1 "
        "aggregate-mode=none mtu=1200"
    )
    primary = (
        f"h264. ! {queue} ! {payloader} ! udpsink host={config.RTP_TARGET_IP} "
        f"port={config.RTP_TARGET_PORT} sync=false async=false "
        f"buffer-size={config.GST_UDP_BUFFER_SIZE}"
    )
    web = (
        f"h264. ! {queue} ! {payloader} ! udpsink host={config.WEBRTC_TARGET_IP} "
        f"port={config.WEBRTC_TARGET_PORT} sync=false async=false "
        f"buffer-size={config.GST_UDP_BUFFER_SIZE}"
    )
    return f"{camera.source} ! {camera.encoder} ! {parsed_stream} {primary} {web}"


class RTPStreamer:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()
        process = self._process
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)

    def run(self) -> int:
        try:
            pipeline = build_pipeline()
            command: Sequence[str] = [
                "gst-launch-1.0", "-e", "-v", *shlex.split(pipeline)
            ]
            LOGGER.info(
                "Camera starting: %dx%d @ %d FPS, H.264 %d bps, GOP %d",
                config.CAMERA_WIDTH,
                config.CAMERA_HEIGHT,
                config.CAMERA_FPS,
                config.VIDEO_BITRATE,
                config.GOP_SIZE,
            )
            LOGGER.info(
                "RTP target: rtp://%s:%d payload=%d",
                config.RTP_TARGET_IP,
                config.RTP_TARGET_PORT,
                config.RTP_PAYLOAD_TYPE,
            )
            LOGGER.info(
                "Windows WebRTC gateway RTP target: rtp://%s:%d",
                config.WEBRTC_TARGET_IP,
                config.WEBRTC_TARGET_PORT,
            )
            self._process = subprocess.Popen(command, text=True)
            LOGGER.info("Camera and RTP pipeline started (PID %d)", self._process.pid)
            while not self._stop_event.wait(0.5):
                return_code = self._process.poll()
                if return_code is not None:
                    if return_code != 0:
                        LOGGER.error("GStreamer pipeline exited with code %d", return_code)
                    return return_code
            return 0
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            LOGGER.error("Camera/RTP startup failed: %s", error)
            return 1
        finally:
            process = self._process
            if process is not None and process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    LOGGER.warning("GStreamer did not stop cleanly; terminating it")
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            self._process = None
            LOGGER.info("Camera and RTP resources released")


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    streamer = RTPStreamer()
    signal.signal(signal.SIGTERM, lambda *_: streamer.stop())
    signal.signal(signal.SIGINT, lambda *_: streamer.stop())
    raise SystemExit(streamer.run())


if __name__ == "__main__":
    main()
