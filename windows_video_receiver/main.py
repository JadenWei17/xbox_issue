"""Run MediaMTX independently from the browser frontend."""

from __future__ import annotations

import logging
import signal
import subprocess
import tempfile
from pathlib import Path

from . import config

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


def render_config() -> Path:
    template = (BASE_DIR / "mediamtx.yml").read_text(encoding="utf-8")
    replacements = {
        "__WEBRTC_PORT__": str(config.MEDIAMTX_WEBRTC_PORT),
        "__ICE_PORT__": str(config.MEDIAMTX_ICE_PORT),
        "__STREAM_PATH__": config.MEDIAMTX_PATH,
        "__UDP_HOST__": config.VIDEO_LISTEN_HOST,
        "__UDP_PORT__": str(config.VIDEO_UDP_PORT),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    handle = tempfile.NamedTemporaryFile(
        mode="w", prefix="robot-mediamtx-", suffix=".yml",
        delete=False, encoding="utf-8",
    )
    try:
        handle.write(template)
    finally:
        handle.close()
    return Path(handle.name)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not config.MEDIAMTX_BINARY.is_file():
        raise SystemExit(f"MediaMTX executable not found: {config.MEDIAMTX_BINARY}")

    runtime_config = render_config()
    process: subprocess.Popen[bytes] | None = None

    def stop(*_: object) -> None:
        if process is not None and process.poll() is None:
            try:
                # CTRL_C_EVENT / SIGINT is unreliable for detached Windows
                # children and can raise WinError 5. MediaMTX handles
                # TerminateProcess cleanup without leaving the UDP port open.
                process.terminate()
            except OSError:
                LOGGER.exception("Could not terminate MediaMTX")

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        process = subprocess.Popen(
            [str(config.MEDIAMTX_BINARY), str(runtime_config)]
        )
        LOGGER.info("MediaMTX receiver started (PID %d)", process.pid)
        LOGGER.info(
            "UDP input: %s:%d; WebRTC: http://127.0.0.1:%d/%s",
            config.VIDEO_LISTEN_HOST, config.VIDEO_UDP_PORT,
            config.MEDIAMTX_WEBRTC_PORT, config.MEDIAMTX_PATH,
        )
        raise SystemExit(process.wait())
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        runtime_config.unlink(missing_ok=True)
        LOGGER.info("MediaMTX receiver stopped")


if __name__ == "__main__":
    main()
