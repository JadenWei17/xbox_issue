"""Serve the viewer UI and supervise an independent MediaMTX WebRTC gateway."""

from __future__ import annotations

import atexit
import logging
import signal
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from .. import video_config as config

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


class MediaMTXGateway:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._runtime_config: Path | None = None

    def _render_config(self) -> Path:
        template = (BASE_DIR / "mediamtx.yml").read_text(encoding="utf-8")
        replacements = {
            "__WEBRTC_PORT__": str(config.MEDIAMTX_WEBRTC_PORT),
            "__ICE_PORT__": str(config.MEDIAMTX_ICE_PORT),
            "__STREAM_PATH__": config.MEDIAMTX_PATH,
            "__RTP_HOST__": config.RTP_LISTEN_HOST,
            "__RTP_PORT__": str(config.WEBRTC_RTP_PORT),
            "__PAYLOAD_TYPE__": str(config.RTP_PAYLOAD_TYPE),
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        handle = tempfile.NamedTemporaryFile(
            mode="w", prefix="robot-mediamtx-", suffix=".yml", delete=False,
            encoding="utf-8"
        )
        try:
            handle.write(template)
        finally:
            handle.close()
        return Path(handle.name)

    def start(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        configuration = self._render_config()
        self._runtime_config = configuration
        try:
            self._process = subprocess.Popen(
                [config.MEDIAMTX_BINARY, str(configuration)], text=True
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"MediaMTX binary '{config.MEDIAMTX_BINARY}' was not found"
            ) from error
        LOGGER.info("MediaMTX WebRTC gateway started (PID %d)", self._process.pid)

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def stop(self) -> None:
        process = self._process
        had_resources = process is not None or self._runtime_config is not None
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                LOGGER.warning("MediaMTX did not stop cleanly; terminating it")
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        self._process = None
        if self._runtime_config is not None:
            self._runtime_config.unlink(missing_ok=True)
            self._runtime_config = None
        if had_resources:
            LOGGER.info("MediaMTX gateway resources released")


gateway = MediaMTXGateway()
app = Flask(__name__)


@app.get("/")
def index() -> str:
    LOGGER.info("Viewer page opened by %s", request.remote_addr)
    return render_template(
        "index.html",
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT,
        fps=config.CAMERA_FPS,
        mediamtx_port=config.MEDIAMTX_WEBRTC_PORT,
        stream_path=config.MEDIAMTX_PATH,
    )


@app.get("/api/status")
def status() -> Response:
    return jsonify(
        gateway=gateway.is_running(),
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT,
        fps=config.CAMERA_FPS,
    )


@app.post("/api/connect")
def connected() -> tuple[str, int]:
    LOGGER.info("Video client connected: %s", request.remote_addr)
    return ("", 204)


@app.post("/api/disconnect")
def disconnected() -> tuple[str, int]:
    LOGGER.info("Video client disconnected: %s", request.remote_addr)
    return ("", 204)


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        gateway.start()
        atexit.register(gateway.stop)

        def terminate(*_: object) -> None:
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, terminate)
        LOGGER.info("Web viewer: http://%s:%d", config.WEB_HOST, config.WEB_PORT)
        LOGGER.info(
            "WebRTC/WHEP endpoint: http://<pi-ip>:%d/%s/whep",
            config.MEDIAMTX_WEBRTC_PORT,
            config.MEDIAMTX_PATH,
        )
        app.run(
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            threaded=True,
            use_reloader=False,
        )
    except (OSError, RuntimeError) as error:
        LOGGER.exception("Web service failed: %s", error)
        raise SystemExit(1) from error
    finally:
        gateway.stop()


if __name__ == "__main__":
    main()
