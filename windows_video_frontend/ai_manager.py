"""Manage the independent robot-yolo AI process from the dashboard."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / ".run"
LOG_DIR = PROJECT_ROOT / "runtime_logs"
PID_FILE = RUN_DIR / "windows-ai.pid"
STATUS_URL = f"http://127.0.0.1:{config.AI_PORT}/api/status"


class AIManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None

    @staticmethod
    def _read_pid() -> int | None:
        try:
            return int(PID_FILE.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _pid_running(pid: int | None) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _api_status() -> dict[str, object] | None:
        try:
            with urllib.request.urlopen(STATUS_URL, timeout=0.3) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return None

    def status(self) -> dict[str, object]:
        pid = self._read_pid()
        running = self._pid_running(pid)
        api = self._api_status() if running else None
        if not running:
            PID_FILE.unlink(missing_ok=True)
        return {
            "local": running,
            "pi": False,
            "running": running,
            "ready": bool(api),
            "online": bool(api and api.get("online")),
            "model": api.get("model") if api else None,
            "error": api.get("error") if api else None,
        }

    def start(self) -> dict[str, object]:
        with self._lock:
            if self._pid_running(self._read_pid()):
                return self.status()
            if not config.ROBOT_YOLO_PYTHON.is_file():
                raise RuntimeError(
                    f"robot-yolo Python was not found: {config.ROBOT_YOLO_PYTHON}"
                )
            RUN_DIR.mkdir(exist_ok=True)
            LOG_DIR.mkdir(exist_ok=True)
            stdout = (LOG_DIR / "windows-ai.stdout.log").open("ab")
            stderr = (LOG_DIR / "windows-ai.stderr.log").open("ab")
            creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                process = subprocess.Popen(
                    [
                        str(config.ROBOT_YOLO_PYTHON),
                        "-m",
                        "windows_ai_service.main",
                    ],
                    cwd=PROJECT_ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    creationflags=creation_flags,
                )
            finally:
                stdout.close()
                stderr.close()
            self._process = process
            PID_FILE.write_text(str(process.pid), encoding="ascii")

        # Allow fast startup failures (bad environment/model/port) to surface.
        for _ in range(20):
            if process.poll() is not None or self._api_status() is not None:
                break
            time.sleep(0.1)
        if process.poll() is not None:
            PID_FILE.unlink(missing_ok=True)
            raise RuntimeError(
                "AI service exited during startup; see runtime_logs/windows-ai.stderr.log"
            )
        return self.status()

    def stop(self) -> dict[str, object]:
        with self._lock:
            pid = self._read_pid()
            if pid is not None and self._pid_running(pid):
                if os.name == "nt":
                    result = subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    if result.returncode != 0 and self._pid_running(pid):
                        detail = result.stderr.strip() or result.stdout.strip()
                        raise RuntimeError(detail or "Could not stop the AI process")
                else:
                    os.kill(pid, 15)
            self._process = None
            PID_FILE.unlink(missing_ok=True)
        return self.status()


ai_manager = AIManager()
