import shutil
import tkinter as tk
from tkinter import ttk

import pytest

from mortalshell_save_manager import __version__, gui
from mortalshell_save_manager.store import SLOT_BASENAMES


def _write_game_files(game):
    for slot in (1, 2):
        for base in SLOT_BASENAMES:
            (game / f"{base}_{slot}.sav").write_text(f"{base}{slot}")


@pytest.fixture(scope="module")
def _window(tmp_path_factory):
    """One main window for the whole module. Opening several Tk roots in one process proved flaky on Windows."""
    base = tmp_path_factory.mktemp("gui")
    game = base / "game"
    game.mkdir()
    _write_game_files(game)
    patches = pytest.MonkeyPatch()
    patches.setattr(gui, "default_save_dir", lambda: game)
    patches.setattr(gui, "data_dir", lambda: base)
    patches.setattr(gui, "find_game_process", lambda: None)
    try:
        window = gui.App()
    except tk.TclError as error:
        patches.undo()
        if "display" in str(error):
            pytest.skip("no display available")
        raise
    window.update()
    yield window, game
    window.destroy()
    patches.undo()


@pytest.fixture
def app(_window, monkeypatch):
    window, game = _window
    for f in game.iterdir():
        f.unlink()
    _write_game_files(game)
    for d in window.store.library_dir.iterdir():
        shutil.rmtree(d)
    monkeypatch.setattr(gui, "game_running", lambda: False)
    window.status.set("")
    window.refresh()
    window.update()
    return window


def find(app, cls):
    return [w for w in app.winfo_children() if isinstance(w, cls)][0]


def fill_create(app, name):
    def go():
        d = find(app, gui.CreateDialog)
        d.name.insert(0, name)
        d._ok()

    return go


def click(app, label):
    def go():
        d = find(app, gui.ConfirmDialog)
        buttons = [w for w in d.winfo_children()[0].winfo_children() if isinstance(w, ttk.Button)]
        next(b for b in buttons if b.cget("text") == label).invoke()

    return go


def test_starts_with_empty_state_and_version_in_title(app):
    assert str(app.empty_label.winfo_manager()) == "place"
    assert str(app.btn_load.cget("state")) == "disabled"
    assert str(app.btn_delete.cget("state")) == "disabled"
    assert f"v{__version__}" in app.title()


def test_cancel_in_running_game_warning_creates_nothing(app, monkeypatch):
    monkeypatch.setattr(gui, "game_running", lambda: True)
    app.after(300, fill_create(app, "Rejected"))
    app.after(700, click(app, "Cancel"))
    app.create_save()
    app.update()
    assert app.tree.get_children() == ()


def test_continue_in_running_game_warning_creates_the_save(app, monkeypatch):
    monkeypatch.setattr(gui, "game_running", lambda: True)
    app.after(300, fill_create(app, "Before Boss"))
    app.after(700, click(app, "Continue"))
    app.create_save()
    app.update()
    assert app.tree.get_children() == ("Before Boss",)
    assert app.tree.selection() == ("Before Boss",)
    assert str(app.btn_load.cget("state")) == "normal"
    assert str(app.empty_label.winfo_manager()) == ""


def test_warning_dialog_text_and_buttons(app, monkeypatch):
    monkeypatch.setattr(gui, "game_running", lambda: True)
    seen = {}

    def peek():
        d = find(app, gui.ConfirmDialog)
        seen["labels"] = [w.cget("text") for w in d.winfo_children()[0].winfo_children()]
        click(app, "Cancel")()

    app.after(300, fill_create(app, "Peek"))
    app.after(700, peek)
    app.create_save()
    app.update()
    assert any("Mortal Shell appears to be running" in t for t in seen["labels"])
    assert "Continue" in seen["labels"]
    assert "Cancel" in seen["labels"]


def test_load_reports_target_slot(app):
    app.after(300, fill_create(app, "Before Boss"))
    app.create_save()
    app.update()

    def load():
        d = find(app, gui.LoadDialog)
        d.slot.set("2")
        d._ok()

    app.after(300, load)
    app.load_save()
    app.update()
    assert "loaded into slot 2" in app.status.get()


def test_delete_asks_first(app):
    app.after(300, fill_create(app, "Before Boss"))
    app.create_save()
    app.update()

    app.after(300, click(app, "Cancel"))
    app.delete_save()
    app.update()
    assert app.tree.get_children() == ("Before Boss",)

    app.after(300, click(app, "Delete"))
    app.delete_save()
    app.update()
    assert app.tree.get_children() == ()
