# Changelog

All notable changes are listed here. The format follows Keep a Changelog.

## [1.2.0]

### Added
- Warning with Continue and Cancel buttons when you create or load a save while the game is running.
- Game status line at the top of the window.
- Project restructured as an installable package with tests, continuous integration and a release build.

### Changed
- The whole interface, README and changelog are in English.
- Dialogs open centered over the main window.
- Running from source stores data in `MortalShellSaveManager` inside the user folder. The packaged `.exe` still stores it next to itself.

### Fixed
- Two loads within the same second no longer fail because of a colliding backup folder name.
- Old backups are now pruned by creation time instead of by folder name.
