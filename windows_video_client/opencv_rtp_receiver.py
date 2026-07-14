"""Low-latency RTP/H.264 input example for future inference on the PC."""

from __future__ import annotations

import argparse
import logging

import cv2

LOGGER = logging.getLogger(__name__)


def pipeline(port: int, payload_type: int) -> str:
    return (
        f"udpsrc port={port} buffer-size=131072 caps=\"application/x-rtp,"
        f"media=video,encoding-name=H264,clock-rate=90000,payload={payload_type}\" ! "
        "rtpjitterbuffer latency=30 drop-on-latency=true ! "
        "rtph264depay ! h264parse ! avdec_h264 max-threads=1 ! "
        "videoconvert ! appsink sync=false drop=true max-buffers=1"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5004)
    parser.add_argument("--payload-type", type=int, default=96)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    capture = cv2.VideoCapture(
        pipeline(args.port, args.payload_type), cv2.CAP_GSTREAMER
    )
    if not capture.isOpened():
        raise RuntimeError("OpenCV could not open the GStreamer RTP pipeline")
    LOGGER.info("Receiving latest RTP frame on UDP port %d", args.port)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                LOGGER.warning("Video frame unavailable")
                continue
            # Run inference on `frame` here. appsink retains at most one frame.
            cv2.imshow("Robot RTP", frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
