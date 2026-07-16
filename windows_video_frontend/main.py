"""Serve the browser UI without managing the video receiver process."""

from __future__ import annotations

import logging
import json
import socket
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from . import config
from .ai_manager import ai_manager
from .service_manager import PAIRS, manager
from .telemetry import TelemetryReceiver
from windows_controller.config import RASPBERRY_PI_IP, RASPBERRY_PI_PORT
from windows_controller.keyboard_input import parse_motion_command

LOGGER = logging.getLogger(__name__)
app = Flask(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTROLLER_STATUS_FILE = PROJECT_ROOT / ".run" / "controller-status.json"
telemetry = TelemetryReceiver(
    config.TELEMETRY_LISTEN_HOST, config.TELEMETRY_LISTEN_PORT
)


def require_local_json() -> None:
    if request.remote_addr not in ("127.0.0.1", "::1"):
        raise PermissionError("Service control is restricted to this computer")
    if not request.is_json:
        raise ValueError("A JSON request is required")


def receiver_available() -> bool:
    host = config.MEDIAMTX_HOST or "127.0.0.1"
    try:
        with socket.create_connection(
            (host, config.MEDIAMTX_WEBRTC_PORT), timeout=0.2
        ):
            return True
    except OSError:
        return False


def controller_mode() -> dict[str, object]:
    try:
        data = json.loads(CONTROLLER_STATUS_FILE.read_text(encoding="utf-8"))
        updated_at = float(data["updated_at"])
        mode = str(data["mode"])
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        return {"mode": "STOPPED", "online": False}
    return {"mode": mode, "online": time.time() - updated_at < 3.0}


@app.get("/")
def index() -> str:
    LOGGER.info("Viewer page opened by %s", request.remote_addr)
    return render_template(
        "index.html",
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT,
        fps=config.CAMERA_FPS,
        mediamtx_host=config.MEDIAMTX_HOST,
        mediamtx_port=config.MEDIAMTX_WEBRTC_PORT,
        stream_path=config.MEDIAMTX_PATH,
    )


@app.get("/api/status")
def status() -> Response:
    return jsonify(
        gateway=receiver_available(), width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT, fps=config.CAMERA_FPS,
    )


@app.get("/api/services")
def services() -> Response:
    statuses = {name: manager.status(name) for name in PAIRS}
    statuses["ai"] = ai_manager.status()
    return jsonify(statuses)


@app.get("/api/robot-status")
def robot_status() -> Response:
    return jsonify(
        telemetry=telemetry.latest(), controller=controller_mode()
    )


@app.post("/api/motion-command")
def motion_command() -> tuple[Response, int] | Response:
    try:
        require_local_json()
        mode = controller_mode()
        if not mode["online"] or mode["mode"] != "DISTANCE_MODE":
            raise RuntimeError("D-pad 尚未切换到 DISTANCE_MODE")
        body = request.get_json()
        text = body.get("command", "") if isinstance(body, dict) else ""
        command = parse_motion_command(str(text))
        payload = json.dumps(command.as_dict(), separators=(",", ":")).encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(payload, (RASPBERRY_PI_IP, RASPBERRY_PI_PORT))
        return jsonify(sent=command.as_dict())
    except (OSError, PermissionError, RuntimeError, ValueError) as error:
        return jsonify(error=str(error)), 400


@app.post("/api/services/<name>/start")
def start_service(name: str) -> tuple[Response, int] | Response:
    try:
        require_local_json()
        return jsonify(ai_manager.start() if name == "ai" else manager.start(name))
    except (OSError, PermissionError, RuntimeError, ValueError) as error:
        LOGGER.error("Could not start %s: %s", name, error)
        return jsonify(error=str(error)), 503


@app.post("/api/services/<name>/stop")
def stop_service(name: str) -> tuple[Response, int] | Response:
    try:
        require_local_json()
        return jsonify(ai_manager.stop() if name == "ai" else manager.stop(name))
    except (OSError, PermissionError, RuntimeError, ValueError) as error:
        LOGGER.error("Could not stop %s: %s", name, error)
        return jsonify(error=str(error)), 503


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
    telemetry.start()
    LOGGER.info("Web viewer: http://%s:%d", config.WEB_HOST, config.WEB_PORT)
    app.run(
        host=config.WEB_HOST, port=config.WEB_PORT,
        threaded=True, use_reloader=False,
    )


if __name__ == "__main__":
    main()
