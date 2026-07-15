"""Publish controller mode for optional local frontend integration."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / ".run"
STATUS_FILE = RUN_DIR / "controller-status.json"


def write_status(mode: str) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"mode": mode, "updated_at": time.time()}),
        encoding="utf-8",
    )
    os.replace(temporary, STATUS_FILE)
