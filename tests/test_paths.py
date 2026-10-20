from pathlib import Path

from mortalshell_save_manager import paths


def test_default_save_dir_ends_with_the_games_layout():
    expected = ("My Games", "MortalShell", "Dungeonhaven", "Saved", "SaveGames")
    assert paths.default_save_dir().parts[-5:] == expected


def test_data_dir_honours_the_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MORTALSHELL_SAVE_MANAGER_HOME", str(tmp_path))
    assert paths.data_dir() == tmp_path


def test_data_dir_for_source_runs_is_in_the_home_folder(monkeypatch):
    monkeypatch.delenv("MORTALSHELL_SAVE_MANAGER_HOME", raising=False)
    assert paths.data_dir() == Path.home() / "MortalShellSaveManager"


def test_data_dir_for_a_packaged_exe_is_beside_the_exe(monkeypatch, tmp_path):
    monkeypatch.delenv("MORTALSHELL_SAVE_MANAGER_HOME", raising=False)
    exe = tmp_path / "MortalShellSaveManager.exe"
    exe.write_text("")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(exe))
    assert paths.data_dir() == tmp_path
