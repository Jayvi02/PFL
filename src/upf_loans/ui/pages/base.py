from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..context import AppContext


class Page(QWidget):
    title = ""
    subtitle = ""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setObjectName("Workspace")
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(28, 22, 28, 24)
        self.root.setSpacing(16)
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(8)
        self.root.addLayout(self.toolbar)
        ctx.events.data_changed.connect(lambda _area: self.refresh() if self.isVisible() else None)

    def refresh(self) -> None:
        """Reload data from the database."""

    def open_with(self, arg) -> None:
        """Navigate here with an argument (e.g. a search text)."""

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)
