"""Detect whether the game is running."""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from pathlib import Path


def _is_windows() -> bool:
    return os.name == "nt"


def _tasklist() -> str:
    try:
        return subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            timeout=10,
        ).stdout
    except Exception:
        return ""


def find_game_process() -> str | None:
    """Name of a running process containing 'mortalshell' (Windows only), else None."""
    if not _is_windows():
        return None
    # Skip our own packaged .exe, whose name also contains 'mortalshell'.
    own = Path(sys.executable).name.lower()
    for row in csv.reader(io.StringIO(_tasklist())):
        if row and "mortalshell" in row[0].lower() and row[0].lower() != own:
            return row[0]
    return None


def game_running() -> bool:
    return find_game_process() is not None
