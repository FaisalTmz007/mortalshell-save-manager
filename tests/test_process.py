from mortalshell_save_manager import process

TASKLIST = (
    '"System","4","Services","0","144 K"\n'
    '"MortalShell-Win64-Shipping.exe","1234","Console","1","2,000,000 K"\n'
)


def _windows(monkeypatch, output):
    monkeypatch.setattr(process, "_is_windows", lambda: True)
    monkeypatch.setattr(process, "_tasklist", lambda: output)


def test_finds_the_game_process(monkeypatch):
    _windows(monkeypatch, TASKLIST)
    assert process.find_game_process() == "MortalShell-Win64-Shipping.exe"
    assert process.game_running() is True


def test_returns_none_when_the_game_is_not_listed(monkeypatch):
    _windows(monkeypatch, '"System","4","Services","0","144 K"\n')
    assert process.find_game_process() is None
    assert process.game_running() is False


def test_ignores_the_programs_own_exe(monkeypatch):
    _windows(monkeypatch, '"MortalShellSaveManager.exe","99","Console","1","50 K"\n')
    monkeypatch.setattr(process.sys, "executable", "/apps/MortalShellSaveManager.exe")
    assert process.find_game_process() is None


def test_returns_none_off_windows(monkeypatch):
    monkeypatch.setattr(process, "_is_windows", lambda: False)
    assert process.find_game_process() is None
