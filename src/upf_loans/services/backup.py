"""Database backup and restore using SQLite's online backup API."""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from .errors import ServiceError

REQUIRED_TABLES = {"employees", "renewal_batches", "renewal_entries", "audit_logs"}


def create_backup(db_path: Path, target_dir: Path, label: str = "manual") -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"upf_loans-{stamp}-{label}.sqlite3"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return target


def list_backups(target_dir: Path) -> list[Path]:
    return sorted(target_dir.glob("upf_loans-*.sqlite3"), reverse=True)


def prune(target_dir: Path, keep: int, label: str = "auto") -> None:
    autos = [p for p in list_backups(target_dir) if p.stem.endswith(f"-{label}")]
    for old in autos[keep:]:
        old.unlink(missing_ok=True)


def auto_backup_if_due(db_path: Path, target_dir: Path, keep: int = 30) -> Path | None:
    """One automatic backup per day, on start-up."""
    if not db_path.exists():
        return None
    today = datetime.now().strftime("%Y%m%d")
    if any(p.name.startswith(f"upf_loans-{today}") and p.stem.endswith("-auto") for p in list_backups(target_dir)):
        return None
    path = create_backup(db_path, target_dir, "auto")
    prune(target_dir, keep)
    return path


def validate_backup(path: Path) -> None:
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ServiceError("The backup file is damaged.")
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        raise ServiceError("The selected file is not a UPF Loan Manager backup.") from exc
    missing = REQUIRED_TABLES - tables
    if missing:
        raise ServiceError("The selected file is not a UPF Loan Manager backup.")


def restore(backup_path: Path, db_path: Path, backup_dir: Path) -> Path:
    """Replace the live database with a backup. A safety copy of the current DB is made first.

    The caller must have closed all connections (dispose the engine) beforehand.
    """
    validate_backup(backup_path)
    safety = create_backup(db_path, backup_dir, "before-restore") if db_path.exists() else None
    for suffix in ("-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)
    shutil.copy2(backup_path, db_path)
    return safety
