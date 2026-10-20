import pytest

from mortalshell_save_manager.store import GLOBAL_FILES, SLOT_BASENAMES, SaveStore


@pytest.fixture
def game_dir(tmp_path):
    """A fake SaveGames folder with two complete slots, game backups and global files."""
    d = tmp_path / "game"
    d.mkdir()
    for slot in (1, 2):
        for base in SLOT_BASENAMES:
            (d / f"{base}_{slot}.sav").write_text(f"{base}-slot{slot}-v1")
            (d / f"{base}_{slot}_bk_1.sav").write_text("game-backup")
    for name in GLOBAL_FILES:
        (d / name).write_text("global-v1")
    return d


@pytest.fixture
def store(tmp_path, game_dir):
    return SaveStore(tmp_path / "library", game_dir)
