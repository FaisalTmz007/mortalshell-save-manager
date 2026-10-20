# Contributing

Bug reports and pull requests are welcome.

## Set up

You need Python 3.9 or newer on Windows.

```
git clone https://github.com/FaisalTmz007/mortalshell-save-manager
cd mortalshell-save-manager
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run the program with `mortalshell-save-manager`.

## Check your change

```
ruff check .
pytest
```

CI runs the same two commands on Python 3.9, 3.12 and 3.13.

Tests that touch saves use temporary folders. Do not point a test at a real `SaveGames` folder.

## Where things are

The code in `src/mortalshell_save_manager/` is split by job. `store.py` copies and tracks snapshots and has no GUI code, so most behavior can be tested without a window. `gui.py` only talks to `SaveStore`. Put new file handling in `store.py` and cover it in `tests/test_store.py`.

## Releasing

1. Change `__version__` in `src/mortalshell_save_manager/__init__.py` and add an entry to `CHANGELOG.md`.
2. Write the release text in `docs/RELEASE_NOTES.md`.
3. Commit, then tag and push: `git tag v1.2.0` and `git push origin v1.2.0`.

The Release workflow builds `MortalShellSaveManager.exe` on a Windows runner, writes its SHA-256 file and attaches both to the GitHub release.
