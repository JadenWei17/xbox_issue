# Windows AI sidecar

This service is intentionally separate from the existing `robot` control and
video processes. It runs with `robot-yolo`, receives the MediaMTX stream over
WHEP/WebRTC, performs YOLO inference, and exposes detection coordinates on
`http://127.0.0.1:8091`.

## Current decision architecture: pure YOLO

The current AI path is **pure YOLO**. Object presence, class identity, bounding
boxes, and confidence values come directly from the loaded YOLO detection
model. There is currently no sensor fusion, rule-based classifier, second-stage
model, tracking-based decision layer, or large-language-model judgment in the
recognition result. The frontend only visualizes the detections returned by
YOLO; it does not change the predicted class.

Start the existing video service first, then run:

```powershell
.\windows_ai_service\start_ai.ps1
```

The main dashboard also contains an **AI 服务** row. Its start button launches
this module with the `robot-yolo` Python interpreter while the dashboard itself
continues to run in the `robot` environment. Runtime output is written to
`runtime_logs/windows-ai.stdout.log` and `runtime_logs/windows-ai.stderr.log`.

Configuration can be overridden with environment variables:

- `YOLO_MODEL_PATH` (default `models/cat_detector/best.pt`)
- `AI_WHEP_URL` (default `http://127.0.0.1:8889/robot/whep`)
- `AI_CONFIDENCE` (default `0.45`)
- `AI_MAX_FPS` (default `10`)
- `AI_DEVICE` (default `0`, the first CUDA GPU)
- `AI_PORT` (default `8091`)
