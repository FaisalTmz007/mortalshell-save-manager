"""Tkinter user interface."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_AUTHOR, APP_TITLE, __version__
from .config import Config
from .paths import data_dir, default_save_dir, documents_dir
from .process import find_game_process, game_running
from .store import AUTOBACKUP_DIR, SaveError, SaveStore

GAME_POLL_MS = 4000


def _icon_path() -> Path | None:
    """assets/icon.ico inside a packaged .exe, or in the repository when run from source."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    path = base / "assets" / "icon.ico"
    return path if path.is_file() else None


def _center_on(win: tk.Toplevel, parent: tk.Misc) -> None:
    win.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 3
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


class ConfirmDialog(tk.Toplevel):
    """Two-button dialog with explicit labels. Cancel is the default button."""

    def __init__(self, parent: tk.Misc, title: str, message: str, ok_text: str = "Continue"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = False

        frm = ttk.Frame(self, padding=16)
        frm.grid(sticky="nsew")
        ttk.Label(frm, text=message, justify="left").grid(row=0, column=0, columnspan=2, sticky="w")

        ok = ttk.Button(frm, text=ok_text, command=self._ok)
        cancel = ttk.Button(frm, text="Cancel", command=self._cancel)
        cancel.grid(row=1, column=1, sticky="e", pady=(16, 0))
        ok.grid(row=1, column=0, sticky="e", padx=(0, 8), pady=(16, 0))
        frm.columnconfigure(0, weight=1)

        for btn in (ok, cancel):
            btn.bind("<Return>", lambda e: e.widget.invoke())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        cancel.focus_set()
        _center_on(self, parent)
        self.grab_set()

    def _ok(self) -> None:
        self.result = True
        self.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.destroy()


class CreateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, slots: list[int]):
        super().__init__(parent)
        self.title("Create save")
        self.transient(parent)
        self.resizable(False, False)
        self.result: dict | None = None

        frm = ttk.Frame(self, padding=14)
        frm.grid(sticky="nsew")
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Name").grid(row=0, column=0, sticky="w", pady=4)
        self.name = ttk.Entry(frm, width=36)
        self.name.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frm, text="Source slot").grid(row=1, column=0, sticky="w", pady=4)
        self.slot = ttk.Combobox(frm, values=[str(s) for s in slots], state="readonly", width=6)
        self.slot.current(0)
        self.slot.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(frm, text="Note").grid(row=2, column=0, sticky="w", pady=4)
        self.note = ttk.Entry(frm, width=36)
        self.note.grid(row=2, column=1, sticky="ew", pady=4)

        self.include_global = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm,
            text="Also include AchievementSave and PlayerSettingsSave",
            variable=self.include_global,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="Save", command=self._ok).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.name.focus_set()
        _center_on(self, parent)
        self.grab_set()

    def _ok(self) -> None:
        self.result = {
            "name": self.name.get(),
            "slot": int(self.slot.get()),
            "note": self.note.get(),
            "include_global": self.include_global.get(),
        }
        self.destroy()


class LoadDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, meta: dict, slots: list[int]):
        super().__init__(parent)
        self.title("Load save")
        self.transient(parent)
        self.resizable(False, False)
        self.result: dict | None = None

        frm = ttk.Frame(self, padding=14)
        frm.grid(sticky="nsew")

        ttk.Label(frm, text=f'Loading "{meta["name"]}" (taken from slot {meta["slot"]}).').grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(frm, text="Overwrite target slot").grid(row=1, column=0, sticky="w", pady=(10, 4))
        values = [str(s) for s in slots]
        self.slot = ttk.Combobox(frm, values=values, state="readonly", width=6)
        self.slot.current(values.index(str(meta["slot"])) if str(meta["slot"]) in values else 0)
        self.slot.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(10, 4))

        self.rm_bk = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frm,
            text="Delete the game's own backup files (_bk_1) in the target slot",
            variable=self.rm_bk,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Label(
            frm,
            text=f"The current state of the target slot is copied to {AUTOBACKUP_DIR} first.",
            foreground="#555555",
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="Load", command=self._ok).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.slot.focus_set()
        _center_on(self, parent)
        self.grab_set()

    def _ok(self) -> None:
        self.result = {"slot": int(self.slot.get()), "remove_game_backups": self.rm_bk.get()}
        self.destroy()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} v{__version__}")
        self.geometry("820x500")
        self.minsize(640, 380)
        icon = _icon_path()
        if icon:
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

        self.config_store = Config(data_dir() / "config.json")
        self.store = SaveStore(data_dir() / "saves", self.config_store.save_dir or default_save_dir())

        self._build_ui()
        self._ensure_game_dir()
        self.refresh()
        self._poll_game()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=(12, 10, 12, 4))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Game save folder:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        ttk.Label(top, textvariable=self.path_var).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(top, text="Change...", command=self.choose_game_dir).grid(row=0, column=2)
        ttk.Button(top, text="Open folder", command=self.open_game_dir).grid(row=0, column=3, padx=(6, 0))

        ttk.Label(top, text="Game status:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.game_var = tk.StringVar(value="checking...")
        self.game_label = ttk.Label(top, textvariable=self.game_var)
        self.game_label.grid(row=1, column=1, columnspan=3, sticky="w", padx=8, pady=(4, 0))

        mid = ttk.Frame(self, padding=(12, 4))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        cols = ("name", "slot", "note", "created")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        for key, text, width, stretch in (
            ("name", "Name", 190, False),
            ("slot", "Slot", 50, False),
            ("note", "Note", 320, True),
            ("created", "Created", 140, False),
        ):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, stretch=stretch, anchor="center" if key == "slot" else "w")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self.empty_label = ttk.Label(
            mid,
            text='No saves yet.\nClick "Create save" to snapshot the slot you are playing.',
            justify="center",
            foreground="#555555",
        )

        bottom = ttk.Frame(self, padding=(12, 6, 12, 4))
        bottom.grid(row=2, column=0, sticky="ew")
        ttk.Button(bottom, text="Create save", command=self.create_save).pack(side="left")
        self.btn_load = ttk.Button(bottom, text="Load", command=self.load_save)
        self.btn_load.pack(side="left", padx=6)
        self.btn_delete = ttk.Button(bottom, text="Delete", command=self.delete_save)
        self.btn_delete.pack(side="left")
        ttk.Button(bottom, text="Open _autobackup", command=self.open_autobackup).pack(side="right")

        footer = ttk.Frame(self, relief="sunken")
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.status = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.status, anchor="w", padding=(8, 3)).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(
            footer,
            text=f"v{__version__}  |  Made by {APP_AUTHOR}",
            foreground="#555555",
            padding=(8, 3),
        ).grid(row=0, column=1, sticky="e")

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons())
        self.tree.bind("<Double-1>", lambda e: self.load_save())
        self.tree.bind("<Return>", lambda e: self.load_save())
        self.tree.bind("<Delete>", lambda e: self.delete_save())
        self.bind("<Control-n>", lambda e: self.create_save())

    def _ensure_game_dir(self) -> None:
        if self.store.game_dir and self.store.game_dir.is_dir():
            self.path_var.set(str(self.store.game_dir))
            return
        self.path_var.set("(not set)")
        messagebox.showinfo(
            APP_TITLE,
            "The Mortal Shell save folder was not found at the default location.\n"
            "Please pick the SaveGames folder manually.",
        )
        self.choose_game_dir()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        saves = self.store.list_saves()
        for m in saves:
            created = m.get("created", "").replace("T", " ")[:16]
            self.tree.insert("", "end", iid=m["name"], values=(m["name"], m["slot"], m.get("note", ""), created))
        if saves:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._update_buttons()

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _update_buttons(self) -> None:
        state = "normal" if self._selected() else "disabled"
        self.btn_load.configure(state=state)
        self.btn_delete.configure(state=state)

    def _set_status(self, text: str) -> None:
        self.status.set(text)

    def _meta(self, name: str) -> dict:
        return next(m for m in self.store.list_saves() if m["name"] == name)

    def _poll_game(self) -> None:
        if os.name != "nt":
            self.game_var.set("detection is only available on Windows")
            return
        proc = find_game_process()
        self.game_var.set(f"RUNNING ({proc})" if proc else "not detected")
        self.after(GAME_POLL_MS, self._poll_game)

    def _confirm(self, title: str, message: str, ok_text: str = "Continue") -> bool:
        dlg = ConfirmDialog(self, title, message, ok_text)
        self.wait_window(dlg)
        return dlg.result

    def choose_game_dir(self) -> None:
        current = self.store.game_dir
        start = str(current) if current and current.is_dir() else str(documents_dir())
        chosen = filedialog.askdirectory(title="Select the Mortal Shell SaveGames folder", initialdir=start)
        if not chosen:
            return
        p = Path(chosen)
        if not list(p.glob("Checkpoints_*.sav")):
            if not self._confirm(
                "Unexpected folder",
                "This folder does not contain any Checkpoints_*.sav files.\nUse it anyway?",
                "Use anyway",
            ):
                return
        self.store.game_dir = p
        self.config_store.save_dir = p
        self.path_var.set(str(p))
        self._set_status("Game save folder updated.")

    def open_game_dir(self) -> None:
        self._open(self.store.game_dir)

    def open_autobackup(self) -> None:
        p = self.store.library_dir / AUTOBACKUP_DIR
        p.mkdir(exist_ok=True)
        self._open(p)

    def _open(self, path: Path | None) -> None:
        if not path or not path.is_dir():
            messagebox.showwarning(APP_TITLE, "Folder not found.")
            return
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _warn_if_running(self, detail: str) -> bool:
        """True if it is fine to go on: the game is not running, or the user chose Continue."""
        if game_running():
            return self._confirm(
                "Mortal Shell is running",
                f"Mortal Shell appears to be running.\n\n{detail}\n\nDo you want to continue anyway?",
                "Continue",
            )
        return True

    def create_save(self) -> None:
        if not self.store.game_dir or not self.store.game_dir.is_dir():
            messagebox.showerror(APP_TITLE, "The game save folder is not set.")
            return
        dlg = CreateDialog(self, self.store.available_slots())
        self.wait_window(dlg)
        if not dlg.result:
            return
        if not self._warn_if_running(
            "Saving while the game is active can produce an inconsistent copy\n"
            "if the game is writing files at that moment. Create the save right after\n"
            "the game saves a checkpoint, not during a loading screen."
        ):
            return
        try:
            meta = self.store.create_save(**dlg.result)
        except SaveError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not create the save: {e}")
            return
        self.refresh()
        self.tree.selection_set(meta["name"])
        self._set_status(f'Save "{meta["name"]}" created from slot {meta["slot"]}.')

    def load_save(self) -> None:
        name = self._selected()
        if not name:
            return
        dlg = LoadDialog(self, self._meta(name), self.store.available_slots())
        self.wait_window(dlg)
        if not dlg.result:
            return
        if not self._warn_if_running(
            "Loading a save while the game is active can fail, or the game may\n"
            "overwrite it again. Quit the game completely first."
        ):
            return
        try:
            backup = self.store.load_save(name, dlg.result["slot"], dlg.result["remove_game_backups"])
        except SaveError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not load the save: {e}")
            return
        msg = f'Save "{name}" loaded into slot {dlg.result["slot"]}.'
        if backup:
            msg += f" Previous slot backed up in {AUTOBACKUP_DIR}/{backup.name}."
        self._set_status(msg)

    def delete_save(self) -> None:
        name = self._selected()
        if not name:
            return
        if not self._confirm(
            "Delete save",
            f'Permanently delete "{name}"?\nThis cannot be undone.\n'
            "Your game's own save files are not affected.",
            "Delete",
        ):
            return
        try:
            self.store.delete_save(name)
        except (SaveError, OSError) as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.refresh()
        self._set_status(f'Save "{name}" deleted.')


def main() -> None:
    App().mainloop()
