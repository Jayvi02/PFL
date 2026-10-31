"""Shared application state passed to every page."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ..db.models import User
from ..db.session import Database


class Events(QObject):
    data_changed = Signal(str)  # area: "employees", "renewals", "settings", ...
    navigate = Signal(str, object)  # page key, optional argument


@dataclass
class AppContext:
    db: Database
    user: User
    events: Events

    @property
    def is_admin(self) -> bool:
        return self.user.is_admin
