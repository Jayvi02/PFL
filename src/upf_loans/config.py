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
APP_VERSION = "0.1.0"


def data_dir() -> Path:
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
