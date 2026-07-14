"""Discover the libcamera source and preferred H.264 encoder."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass

from . import video_config as config

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraPipeline:
    source: str
    encoder: str
    encoder_name: str


def _has_element(name: str) -> bool:
    result = subprocess.run(
        ["gst-inspect-1.0", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def discover_camera_pipeline() -> CameraPipeline:
    """Validate GStreamer/libcamera and select hardware H.264 when present."""
    if shutil.which("gst-launch-1.0") is None or shutil.which("gst-inspect-1.0") is None:
        raise RuntimeError("GStreamer tools are not installed or not in PATH")
    if not _has_element("libcamerasrc"):
        raise RuntimeError(
            "GStreamer libcamerasrc is unavailable; install the Raspberry Pi "
            "libcamera GStreamer package"
        )

    source = (
        "libcamerasrc ! "
        f"video/x-raw,width={config.CAMERA_WIDTH},height={config.CAMERA_HEIGHT},"
        f"framerate={config.CAMERA_FPS}/1,format=NV12 ! "
        f"queue max-size-buffers={config.GST_QUEUE_BUFFERS} "
        "max-size-bytes=0 max-size-time=0 leaky=downstream"
    )

    if _has_element("v4l2h264enc"):
        controls = (
            "controls,"
            f"video_bitrate={config.VIDEO_BITRATE},"
            f"h264_i_frame_period={config.GOP_SIZE},"
            "repeat_sequence_header=1"
        )
        encoder = (
            f"v4l2h264enc extra-controls={controls} ! "
            "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au"
        )
        return CameraPipeline(source, encoder, "v4l2h264enc (hardware)")

    if not _has_element("x264enc"):
        raise RuntimeError("Neither v4l2h264enc nor x264enc is available")
    LOGGER.warning("Hardware H.264 encoder unavailable; using x264enc software fallback")
    encoder = (
        f"x264enc bitrate={max(1, config.VIDEO_BITRATE // 1000)} "
        f"key-int-max={config.GOP_SIZE} bframes=0 tune=zerolatency "
        "speed-preset=ultrafast byte-stream=true ! "
        "video/x-h264,profile=baseline,stream-format=byte-stream,alignment=au"
    )
    return CameraPipeline(source, encoder, "x264enc (software fallback)")
