"""HTTP API entry point for the independent robot-yolo process."""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify

from . import config
from .inference import worker
from .state import state

app = Flask(__name__)


@app.after_request
def allow_local_dashboard(response: Response) -> Response:
    # Read-only API; allow both localhost and 127.0.0.1 dashboard URLs.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/status")
def status() -> Response:
    snapshot = state.snapshot()
    return jsonify(
        online=snapshot["online"],
        stream=snapshot["stream"],
        stale=snapshot["stale"],
        model=snapshot["model"],
        device=snapshot["device"],
        error=snapshot["error"],
    )


@app.get("/api/detections")
def detections() -> Response:
    return jsonify(state.snapshot())


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    worker.start()
    app.run(host=config.AI_HOST, port=config.AI_PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
