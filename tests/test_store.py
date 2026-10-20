import pytest

from mortalshell_save_manager.store import (
    AUTOBACKUP_DIR,
    AUTOBACKUP_KEEP,
    GLOBAL_FILES,
    SLOT_BASENAMES,
    SaveError,
    SaveStore,
)


def test_empty_library_lists_nothing(store):
    assert store.list_saves() == []


def test_available_slots_from_game_folder(store):
    assert store.available_slots() == [1, 2]


def test_available_slots_defaults_when_folder_has_no_saves(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert SaveStore(tmp_path / "lib", empty).available_slots() == [1, 2]


def test_create_save_records_metadata(store):
    meta = store.create_save("Before Boss", 1, " a note ", include_global=True)
    assert meta["name"] == "Before Boss"
    assert meta["slot"] == 1
    assert meta["note"] == "a note"
    assert meta["globals"] == list(GLOBAL_FILES)
    assert [m["name"] for m in store.list_saves()] == ["Before Boss"]


def test_create_save_without_globals(store):
    meta = store.create_save("Plain", 1)
    assert meta["globals"] == []


@pytest.mark.parametrize("bad", ["", "   ", "a/b", "a:b", "_hidden", "trailing.", "x" * 61])
def test_invalid_names_are_rejected(store, bad):
    with pytest.raises(SaveError):
        store.create_save(bad, 1)


def test_duplicate_name_is_rejected_ignoring_case(store):
    store.create_save("Before Boss", 1)
    with pytest.raises(SaveError):
        store.create_save("before boss", 1)


def test_incomplete_slot_is_rejected_and_leaves_no_folder(store, game_dir):
    (game_dir / "MapState_2.sav").unlink()
    with pytest.raises(SaveError, match="MapState_2.sav"):
        store.create_save("broken", 2)
    assert not (store.library_dir / "broken").exists()


def test_create_without_game_folder_fails(tmp_path):
    with pytest.raises(SaveError):
        SaveStore(tmp_path / "lib", None).create_save("x", 1)


def test_load_into_another_slot(store, game_dir):
    store.create_save("Before Boss", 1)
    for base in SLOT_BASENAMES:
        (game_dir / f"{base}_1.sav").write_text("changed")
    (game_dir / "MapState_2.sav").write_text("old-map2")

    backup = store.load_save("Before Boss", 2, remove_game_backups=True)

    assert (game_dir / "Checkpoints_2.sav").read_text() == "Checkpoints-slot1-v1"
    assert (game_dir / "MapState_2.sav").read_text() == "MapState-slot1-v1"
    assert not (game_dir / "Checkpoints_2_bk_1.sav").exists()
    assert (game_dir / "Checkpoints_1.sav").read_text() == "changed"
    assert (backup / "MapState_2.sav").read_text() == "old-map2"
    assert not list(game_dir.glob("*.tmp"))


def test_load_can_keep_the_games_backup_files(store, game_dir):
    store.create_save("Before Boss", 1)
    store.load_save("Before Boss", 1, remove_game_backups=False)
    assert (game_dir / "Checkpoints_1_bk_1.sav").exists()


def test_load_restores_global_files_only_when_saved(store, game_dir):
    store.create_save("With globals", 1, include_global=True)
    store.create_save("No globals", 1, include_global=False)
    (game_dir / "AchievementSave.sav").write_text("global-v2")

    store.load_save("No globals", 1)
    assert (game_dir / "AchievementSave.sav").read_text() == "global-v2"

    store.load_save("With globals", 1)
    assert (game_dir / "AchievementSave.sav").read_text() == "global-v1"


def test_load_unknown_save_fails(store):
    with pytest.raises(SaveError):
        store.load_save("nope", 1)


def test_load_with_missing_snapshot_file_changes_nothing(store, game_dir):
    store.create_save("Before Boss", 1)
    (store.library_dir / "Before Boss" / "GPData.sav").unlink()
    with pytest.raises(SaveError, match="GPData.sav"):
        store.load_save("Before Boss", 1)
    assert (game_dir / "GPData_1.sav").read_text() == "GPData-slot1-v1"


def test_repeated_loads_in_one_second_do_not_collide_and_old_backups_are_pruned(store):
    store.create_save("Before Boss", 1)
    for _ in range(AUTOBACKUP_KEEP + 3):
        store.load_save("Before Boss", 1)
    backups = list((store.library_dir / AUTOBACKUP_DIR).iterdir())
    assert len(backups) == AUTOBACKUP_KEEP


def test_autobackup_folder_is_not_listed_as_a_save(store):
    store.create_save("Before Boss", 1)
    store.load_save("Before Boss", 1)
    assert [m["name"] for m in store.list_saves()] == ["Before Boss"]


def test_delete_removes_snapshot_but_not_game_files(store, game_dir):
    store.create_save("Before Boss", 1)
    store.delete_save("Before Boss")
    assert store.list_saves() == []
    assert (game_dir / "Checkpoints_1.sav").exists()


def test_delete_unknown_save_fails(store):
    with pytest.raises(SaveError):
        store.delete_save("nope")
