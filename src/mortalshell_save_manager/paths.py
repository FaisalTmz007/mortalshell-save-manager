"""Where the program keeps its data and where the game keeps its saves."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Folder for the snapshot library and the settings file."""
    override = os.environ.get("MORTALSHELL_SAVE_MANAGER_HOME")
    if override:
        return Path(override)
    # A packaged .exe keeps its data beside itself so the tool stays portable.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.home() / "MortalShellSaveManager"


def documents_dir() -> Path:
    """The real Documents folder on Windows (handles Documents moved to OneDrive, etc.)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


def default_save_dir() -> Path:
    return documents_dir() / "My Games" / "MortalShell" / "Dungeonhaven" / "Saved" / "SaveGames"
