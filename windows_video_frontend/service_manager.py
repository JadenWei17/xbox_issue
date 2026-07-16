"""Start and stop the independent Windows/Pi service pairs."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from . import config

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / ".run"
LOG_DIR = PROJECT_ROOT / "runtime_logs"


@dataclass(frozen=True)
class ServicePair:
    local_module: str
    remote_unit: str


PAIRS = {
    "control": ServicePair("windows_controller.main", "robot-control.service"),
    "video": ServicePair("windows_video_receiver.main", "robot-video.service"),
}


class ServiceManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processes: dict[str, subprocess.Popen[bytes]] = {}

    def _pair(self, name: str) -> ServicePair:
        try:
            return PAIRS[name]
        except KeyError as error:
            raise ValueError(f"Unknown service: {name}") from error

    def _pid_file(self, name: str) -> Path:
        return RUN_DIR / f"windows-{name}.pid"

    def _read_pid(self, name: str) -> int | None:
        try:
            return int(self._pid_file(name).read_text(encoding="ascii").strip())
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

    def _ssh(self, arguments: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        command = [
            "ssh", "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={config.SSH_CONNECT_TIMEOUT_SECONDS}",
            config.PI_SSH_TARGET, *arguments,
        ]
        try:
            result = subprocess.run(
                command, text=True, capture_output=True,
                timeout=config.SSH_CONNECT_TIMEOUT_SECONDS + 3,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Timed out while connecting to the Pi over SSH") from error
        if check and result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(detail or f"SSH exited with code {result.returncode}")
        return result

    def _remote_active(self, unit: str) -> bool:
        try:
            result = self._ssh(["systemctl", "is-active", unit], check=False)
            return result.returncode == 0 and result.stdout.strip() == "active"
        except (OSError, subprocess.TimeoutExpired):
            return False

    def status(self, name: str) -> dict[str, bool]:
        pair = self._pair(name)
        pid = self._read_pid(name)
        local = self._pid_running(pid)
        if pid is not None and not local:
            self._pid_file(name).unlink(missing_ok=True)
        remote = self._remote_active(pair.remote_unit)
        return {
            "local": local,
            "pi": remote,
            "running": local and remote,
        }

    def _start_local(self, name: str, module: str) -> None:
        old_pid = self._read_pid(name)
        if self._pid_running(old_pid):
            return
        RUN_DIR.mkdir(exist_ok=True)
        LOG_DIR.mkdir(exist_ok=True)
        stdout = (LOG_DIR / f"windows-{name}.stdout.log").open("ab")
        stderr = (LOG_DIR / f"windows-{name}.stderr.log").open("ab")
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", module], cwd=PROJECT_ROOT,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                creationflags=creation_flags,
            )
        finally:
            stdout.close()
            stderr.close()
        self._processes[name] = process
        self._pid_file(name).write_text(str(process.pid), encoding="ascii")
        LOGGER.info("Windows %s service started (PID %d)", name, process.pid)

    def _stop_local(self, name: str) -> None:
        pid = self._read_pid(name)
        process = self._processes.get(name)
        target_pid = process.pid if process is not None and process.poll() is None else pid
        if target_pid is not None and self._pid_running(target_pid):
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(target_pid), "/T", "/F"],
                    text=True, capture_output=True, check=False,
                )
                if result.returncode != 0 and self._pid_running(target_pid):
                    detail = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(detail or "Could not stop Windows process tree")
            else:
                os.kill(target_pid, signal.SIGTERM)
        self._processes.pop(name, None)
        self._pid_file(name).unlink(missing_ok=True)

    def start(self, name: str) -> dict[str, bool]:
        pair = self._pair(name)
        with self._lock:
            if name == "video":
                self._start_local(name, pair.local_module)
                self._ssh(["sudo", "-n", "systemctl", "start", pair.remote_unit])
            else:
                self._ssh(["sudo", "-n", "systemctl", "start", pair.remote_unit])
                self._start_local(name, pair.local_module)
        return self.status(name)

    def stop(self, name: str) -> dict[str, bool]:
        pair = self._pair(name)
        with self._lock:
            # Stop the Windows command sender before stopping Pi control.
            local_error: Exception | None = None
            try:
                self._stop_local(name)
            except (OSError, RuntimeError) as error:
                local_error = error
            self._ssh(["sudo", "-n", "systemctl", "stop", pair.remote_unit])
            if local_error is not None:
                raise RuntimeError(f"Pi stopped, but Windows cleanup failed: {local_error}")
        return self.status(name)


manager = ServiceManager()
