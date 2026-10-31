"""Shared application state passed to every page."""

from __future__ import annotations

import getpass
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal

from ..db.session import Database


class Events(QObject):
    data_changed = Signal(str)  # area: "employees", "renewals", "settings", ...
    navigate = Signal(str, object)  # page key, optional argument
    update_found = Signal(object)  # updater.UpdateInfo when GitHub has a newer build


def current_operator() -> str:
    """The Windows account name, recorded in the audit log."""
    try:
        return getpass.getuser() or "officer"
    except Exception:  # noqa: BLE001 - no login name available
        return "officer"


@dataclass
class AppContext:
    db: Database
    events: Events
    operator: str = field(default_factory=current_operator)
