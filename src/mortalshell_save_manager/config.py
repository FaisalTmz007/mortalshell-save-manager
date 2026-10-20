"""Persistent program settings."""

from __future__ import annotations

import json
from pathlib import Path


class Config:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = {}
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    @property
    def save_dir(self) -> Path | None:
        value = self.data.get("save_dir")
        return Path(value) if value else None

    @save_dir.setter
    def save_dir(self, p: Path) -> None:
        self.data["save_dir"] = str(p)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
