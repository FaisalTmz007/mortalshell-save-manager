from mortalshell_save_manager.config import Config


def test_missing_file_gives_no_save_dir(tmp_path):
    assert Config(tmp_path / "config.json").save_dir is None


def test_save_dir_round_trips_through_disk(tmp_path):
    path = tmp_path / "nested" / "config.json"
    Config(path).save_dir = tmp_path / "SaveGames"
    assert Config(path).save_dir == tmp_path / "SaveGames"


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    assert Config(path).save_dir is None
