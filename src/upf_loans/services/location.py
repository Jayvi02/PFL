"""Moving the data folder (database and backups) somewhere else, e.g. D:\\UPFLoans."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from .. import config
from .errors import ServiceError

DB_NAME = "upf_loans.sqlite3"


def move_data(target: Path) -> Path:
    """Copy the database and backups into ``target`` and point the app at it.

    The old files are left where they were, as a fallback. The caller must close
    the database first and restart the app afterwards.
    """
    target = Path(target).resolve()
    source = config.data_dir().resolve()
    if target == source:
        raise ServiceError("The data is already in that folder.")
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        raise ServiceError(f"The app can't write to {target}: {exc.strerror or exc}") from exc
    if (target / DB_NAME).exists():
        raise ServiceError(f"{target} already has a UPF Loans database. Choose an empty folder.")

    src = sqlite3.connect(source / DB_NAME)
    dst = sqlite3.connect(target / DB_NAME)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    old_backups = source / "backups"
    if old_backups.is_dir():
        shutil.copytree(old_backups, target / "backups", dirs_exist_ok=True)

    config.set_data_dir(None if target == config.home_dir().resolve() else target)
    return target
