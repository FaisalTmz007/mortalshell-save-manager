"""Snapshot library: create, list, load and delete save snapshots."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

# Per-slot files: <Name>_<slot>.sav, with the game's own backup <Name>_<slot>_bk_1.sav
SLOT_BASENAMES = ("Checkpoints", "GPData", "MapState")
# Global files, not tied to a slot
GLOBAL_FILES = ("AchievementSave.sav", "PlayerSettingsSave.sav")

AUTOBACKUP_DIR = "_autobackup"
AUTOBACKUP_KEEP = 10
INVALID_NAME_CHARS = set('<>:"/\\|?*')


class SaveError(Exception):
    """An error whose message is safe to show directly to the user."""


class SaveStore:
    def __init__(self, library_dir: Path, game_dir: Path | None):
        self.library_dir = Path(library_dir)
        self.game_dir = Path(game_dir) if game_dir else None
        self.library_dir.mkdir(parents=True, exist_ok=True)

    def _require_game_dir(self) -> Path:
        if not self.game_dir or not self.game_dir.is_dir():
            raise SaveError("The game save folder is not set or could not be found.")
        return self.game_dir

    @staticmethod
    def slot_file(base: str, slot: int) -> str:
        return f"{base}_{slot}.sav"

    @staticmethod
    def slot_bk_file(base: str, slot: int) -> str:
        return f"{base}_{slot}_bk_1.sav"

    def available_slots(self) -> list[int]:
        slots = set()
        if self.game_dir and self.game_dir.is_dir():
            for p in self.game_dir.iterdir():
                m = re.fullmatch(r"Checkpoints_(\d+)\.sav", p.name)
                if m:
                    slots.add(int(m.group(1)))
        return sorted(slots) or [1, 2]

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise SaveError("The save name cannot be empty.")
        if len(name) > 60:
            raise SaveError("The save name can be at most 60 characters.")
        if any(c in INVALID_NAME_CHARS for c in name) or name.endswith("."):
            raise SaveError('The name cannot contain  < > : " / \\ | ? *  or end with a period.')
        if name.startswith("_"):
            raise SaveError("The name cannot start with an underscore.")
        return name

    def _save_path(self, name: str) -> Path:
        return self.library_dir / name

    def _name_exists(self, name: str) -> bool:
        low = name.lower()
        return any(p.name.lower() == low for p in self.library_dir.iterdir() if p.is_dir())

    @staticmethod
    def _copy_atomic(src: Path, dst: Path) -> None:
        tmp = dst.with_name(dst.name + ".tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)

    def list_saves(self) -> list[dict]:
        result = []
        for d in sorted(self.library_dir.iterdir()):
            meta_file = d / "meta.json"
            if d.is_dir() and not d.name.startswith("_") and meta_file.is_file():
                try:
                    result.append(json.loads(meta_file.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        result.sort(key=lambda m: m.get("created", ""), reverse=True)
        return result

    def create_save(self, name: str, slot: int, note: str = "", include_global: bool = False) -> dict:
        game = self._require_game_dir()
        name = self.validate_name(name)
        if self._name_exists(name):
            raise SaveError(f'A save named "{name}" already exists. Pick another name.')

        sources = {base: game / self.slot_file(base, slot) for base in SLOT_BASENAMES}
        missing = [p.name for p in sources.values() if not p.is_file()]
        if missing:
            raise SaveError(f"Slot {slot} is incomplete. These files were not found:\n" + "\n".join(missing))

        dest = self._save_path(name)
        dest.mkdir()
        try:
            for base, src in sources.items():
                shutil.copy2(src, dest / f"{base}.sav")
            globals_saved = []
            if include_global:
                for fname in GLOBAL_FILES:
                    src = game / fname
                    if src.is_file():
                        shutil.copy2(src, dest / fname)
                        globals_saved.append(fname)
            meta = {
                "name": name,
                "slot": slot,
                "note": note.strip(),
                "created": datetime.now().isoformat(timespec="seconds"),
                "globals": globals_saved,
            }
            (dest / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
        return meta

    def _autobackup(self, slot: int) -> Path | None:
        """Copy the current state of the target slot before it is overwritten."""
        game = self._require_game_dir()
        files = []
        for base in SLOT_BASENAMES:
            files += [self.slot_file(base, slot), self.slot_bk_file(base, slot)]
        files += list(GLOBAL_FILES)
        existing = [game / f for f in files if (game / f).is_file()]
        if not existing:
            return None
        root = self.library_dir / AUTOBACKUP_DIR
        root.mkdir(exist_ok=True)
        stamp = f"{datetime.now():%Y%m%d-%H%M%S}_slot{slot}"
        dest = root / stamp
        n = 2
        while dest.exists():
            dest = root / f"{stamp}_{n}"
            n += 1
        dest.mkdir()
        for src in existing:
            shutil.copy2(src, dest / src.name)
        # Order by creation time: names created within one second do not sort chronologically.
        backups = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime_ns)
        for p in backups[:-AUTOBACKUP_KEEP]:
            shutil.rmtree(p, ignore_errors=True)
        return dest

    def load_save(self, name: str, target_slot: int, remove_game_backups: bool = True) -> Path | None:
        game = self._require_game_dir()
        src_dir = self._save_path(name)
        meta_file = src_dir / "meta.json"
        if not meta_file.is_file():
            raise SaveError(f'Save "{name}" was not found.')
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

        for base in SLOT_BASENAMES:
            if not (src_dir / f"{base}.sav").is_file():
                raise SaveError(f"{base}.sav is missing from this save. Nothing was changed.")

        backup = self._autobackup(target_slot)

        for base in SLOT_BASENAMES:
            self._copy_atomic(src_dir / f"{base}.sav", game / self.slot_file(base, target_slot))
            if remove_game_backups:
                bk = game / self.slot_bk_file(base, target_slot)
                if bk.is_file():
                    bk.unlink()
        for fname in meta.get("globals", []):
            if (src_dir / fname).is_file():
                self._copy_atomic(src_dir / fname, game / fname)
        return backup

    def delete_save(self, name: str) -> None:
        path = self._save_path(name)
        if not (path / "meta.json").is_file():
            raise SaveError(f'Save "{name}" was not found.')
        shutil.rmtree(path)
