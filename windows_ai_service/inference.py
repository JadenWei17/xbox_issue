"""WebRTC receive loop and YOLO inference worker."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from pathlib import Path

from ultralytics import YOLO

from . import config
from .state import state
from .webrtc import connect, disconnect

LOGGER = logging.getLogger(__name__)


class InferenceWorker:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._model: YOLO | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="yolo-inference", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as error:  # keep the dashboard alive if the worker fails
            LOGGER.exception("AI worker stopped")
            state.update(stream=False, error=str(error), detections=[])

    def _load_model(self) -> YOLO:
        if not config.MODEL_PATH.is_file():
            raise FileNotFoundError(f"YOLO model not found: {config.MODEL_PATH}")
        LOGGER.info("Loading YOLO model: %s", config.MODEL_PATH)
        model = YOLO(str(config.MODEL_PATH))
        state.update(model=config.MODEL_PATH.name, device=config.DEVICE, error=None)
        return model

    def _predict(self, image: object) -> tuple[list[dict[str, object]], int, int]:
        assert self._model is not None
        height, width = image.shape[:2]
        result = self._model.predict(
            source=image,
            conf=config.CONFIDENCE,
            iou=config.IOU,
            imgsz=config.IMAGE_SIZE,
            device=config.DEVICE,
            verbose=False,
        )[0]
        detections: list[dict[str, object]] = []
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            x1, y1, x2, y2 = (round(float(value), 2) for value in box.xyxy[0].tolist())
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": str(names[class_id]),
                    "confidence": round(float(box.conf[0].item()), 4),
                    "box": [x1, y1, x2, y2],
                }
            )
        return detections, width, height

    async def _run(self) -> None:
        self._model = await asyncio.to_thread(self._load_model)
        frame_interval = 1.0 / config.MAX_FPS
        while not self._stop.is_set():
            pc = None
            session_url = None
            try:
                state.update(stream=False, error="Waiting for the MediaMTX video stream", detections=[])
                pc, track, session_url = await connect(config.WHEP_URL)
                state.update(stream=True, error=None)
                LOGGER.info("AI connected to %s", config.WHEP_URL)
                last_inference = 0.0
                while not self._stop.is_set():
                    frame = await track.recv()
                    now = time.monotonic()
                    if now - last_inference < frame_interval:
                        continue
                    last_inference = now
                    image = frame.to_ndarray(format="bgr24")
                    detections, width, height = await asyncio.to_thread(self._predict, image)
                    state.update(
                        stream=True,
                        error=None,
                        width=width,
                        height=height,
                        detections=detections,
                        updated_at=time.time(),
                    )
            except Exception as error:
                if not self._stop.is_set():
                    LOGGER.warning("AI stream unavailable: %s", error)
                    state.update(stream=False, error=str(error), detections=[])
                    await asyncio.sleep(2)
            finally:
                if pc is not None:
                    await disconnect(pc, session_url)


worker = InferenceWorker()
