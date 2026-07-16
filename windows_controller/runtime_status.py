"""Publish controller mode for optional local frontend integration."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / ".run"
STATUS_FILE = RUN_DIR / "controller-status.json"
LOGGER = logging.getLogger(__name__)
REPLACE_ATTEMPTS = 8


def write_status(mode: str) -> bool:
    """Publish the latest mode without allowing UI file locks to stop control."""

    RUN_DIR.mkdir(exist_ok=True)
    temporary = RUN_DIR / f"controller-status-{os.getpid()}-{threading.get_ident()}.tmp"
    try:
        temporary.write_text(
            json.dumps({"mode": mode, "updated_at": time.time()}),
            encoding="utf-8",
        )
        for attempt in range(REPLACE_ATTEMPTS):
            try:
                os.replace(temporary, STATUS_FILE)
                return True
            except PermissionError:
                if attempt + 1 < REPLACE_ATTEMPTS:
                    time.sleep(0.01 * (attempt + 1))
        LOGGER.warning("Controller status file is busy; control loop will continue")
        return False
    except OSError as error:
        LOGGER.warning("Could not publish controller status: %s", error)
        return False
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
