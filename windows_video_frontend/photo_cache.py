"""Persistent desktop storage for JPEG snapshots captured from the live view."""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import BinaryIO


class PhotoCache:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._directory = Path(
            os.getenv("ROBOT_PHOTO_DIR", str(Path.home() / "Desktop" / "RobotPhotos"))
        ).expanduser()
        self._directory.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, dict[str, object]] = {}
        self._load_existing()

    def add(self, stream: BinaryIO, requested_name: str = "cat") -> dict[str, object]:
        now = time.time()
        base_name = Path(requested_name).stem.strip() or "cat"
        base_name = re.sub(r"[^\w.-]+", "_", base_name, flags=re.UNICODE).strip("._")
        base_name = base_name[:80] or "cat"
        with self._lock:
            pattern = re.compile(rf"^{re.escape(base_name)}_(\d{{3,}})\.jpg$", re.IGNORECASE)
            sequence = max(
                (
                    int(match.group(1))
                    for path in self._directory.glob(f"{base_name}_*.jpg")
                    if (match := pattern.match(path.name))
                ),
                default=0,
            ) + 1
            filename = f"{base_name}_{sequence:03d}.jpg"
            photo_id = Path(filename).stem
            path = self._directory / filename
            with path.open("xb") as output:
                while chunk := stream.read(1024 * 1024):
                    output.write(chunk)
        if path.stat().st_size == 0:
            path.unlink(missing_ok=True)
            raise ValueError("The uploaded photo is empty")
        with path.open("rb") as image:
            if image.read(2) != b"\xff\xd8":
                path.unlink(missing_ok=True)
                raise ValueError("The uploaded file is not a JPEG image")
        entry = {
            "id": photo_id,
            "filename": filename,
            "content_type": "image/jpeg",
            "created_at": now,
            "size_bytes": path.stat().st_size,
            "path": path,
        }
        with self._lock:
            self._entries[photo_id] = entry
        return self._public(entry)

    def _load_existing(self) -> None:
        for path in self._directory.glob("*.jpg"):
            try:
                created_at = path.stat().st_mtime
                with path.open("rb") as image:
                    if image.read(2) != b"\xff\xd8":
                        continue
            except OSError:
                continue
            photo_id = path.stem
            self._entries[photo_id] = {
                "id": photo_id,
                "filename": path.name,
                "content_type": "image/jpeg",
                "created_at": created_at,
                "size_bytes": path.stat().st_size,
                "path": path,
            }

    def list(self) -> list[dict[str, object]]:
        with self._lock:
            self._load_existing()
            missing_ids = [
                photo_id
                for photo_id, entry in self._entries.items()
                if not Path(entry["path"]).is_file()
            ]
            for photo_id in missing_ids:
                del self._entries[photo_id]
            entries = sorted(
                self._entries.values(),
                key=lambda item: float(item["created_at"]),
                reverse=True,
            )
            return [self._public(entry) for entry in entries]

    @property
    def directory(self) -> Path:
        return self._directory

    def path_for(self, photo_id: str) -> Path:
        with self._lock:
            entry = self._entries.get(photo_id)
            if entry is None:
                raise KeyError(photo_id)
            path = Path(entry["path"])
            if not path.is_file():
                del self._entries[photo_id]
                raise KeyError(photo_id)
            return path

    @staticmethod
    def _public(entry: dict[str, object]) -> dict[str, object]:
        return {key: value for key, value in entry.items() if key != "path"}

    def close(self) -> None:
        # Photos are intentionally persistent and remain on the desktop.
        with self._lock:
            self._entries.clear()


photo_cache = PhotoCache()
