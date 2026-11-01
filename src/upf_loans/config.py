"""Application paths and constants.

The database and backups live in the user's application-data folder
(%LOCALAPPDATA%\\UPFLoans on Windows), never in the install folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "UPF Loan Manager"
APP_DIR_NAME = "UPFLoans"
APP_VERSION = "1.0"  # the GitHub build appends its run number, e.g. 1.0.42


LOCATION_FILE = "data-location.txt"


class DataLocationError(RuntimeError):
    """The data folder chosen in Settings can't be reached (e.g. a drive is missing)."""


def home_dir() -> Path:
    """This Windows user's own app folder. It always holds the pointer to the data folder."""
    override = os.environ.get("UPF_LOANS_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def chosen_data_dir() -> Path | None:
    """The data folder picked in Settings → Backup & restore, if one was picked."""
    pointer = home_dir() / LOCATION_FILE
    try:
        text = pointer.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return Path(text) if text else None


def set_data_dir(path: Path | None) -> None:
    pointer = home_dir() / LOCATION_FILE
    if path is None:
        pointer.unlink(missing_ok=True)
    else:
        pointer.write_text(str(path), encoding="utf-8")


def data_dir() -> Path:
    """Where the database, backups and log live: the chosen folder, or the user's app folder."""
    chosen = chosen_data_dir()
    if chosen is None:
        return home_dir()
    try:
        chosen.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DataLocationError(
            f"The data folder {chosen} can't be reached ({exc.strerror or exc}).\n\n"
            f"Connect the drive or folder and start the app again. To go back to the default folder, "
            f"delete {home_dir() / LOCATION_FILE}."
        ) from exc
    return chosen


def database_path() -> Path:
    return data_dir() / "upf_loans.sqlite3"


def backup_dir() -> Path:
    path = data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_dir() -> Path:
    """Folder holding bundled resources (works inside a PyInstaller exe)."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "upf_loans"
    return Path(__file__).resolve().parent
