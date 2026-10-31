"""Reusable widgets: cards, stat tiles, money input, banners, dialogs."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ...core.money import MoneyError, format_money, to_decimal
from .. import theme
from ..icons import icon


def button(text: str, icon_name: str | None = None, variant: str | None = None, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    if icon_name:
        color = theme.ON_LIME if variant == "primary" else (theme.DANGER if variant == "danger" else theme.TEXT_SOFT)
        btn.setIcon(icon(icon_name, color))
    if variant:
        btn.setProperty("variant", variant)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class Card(QFrame):
    """A glass panel. ``accent=True`` gives the solid lime version used for the headline figure."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None, accent: bool = False):
        super().__init__(parent)
        self.setObjectName("Card")
        if accent:
            self.setProperty("accent", True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(20, 18, 20, 18)
        self.body.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("CardTitle")
            self.body.addWidget(lbl)


class StatCard(Card):
    def __init__(self, label: str, icon_name: str, parent: QWidget | None = None, accent: bool = False):
        super().__init__(parent=parent, accent=accent)
        top = QHBoxLayout()
        cap = QLabel(label)
        cap.setObjectName("StatLabel")
        cap.setWordWrap(True)
        badge = QLabel()
        badge.setObjectName("Badge")
        badge.setPixmap(icon(icon_name, theme.ON_LIME if accent else theme.LIME, 18).pixmap(18, 18))
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(cap, 1, Qt.AlignmentFlag.AlignTop)
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        self.value = QLabel("–")
        self.value.setObjectName("StatValue")
        self.body.addLayout(top)
        self.body.addStretch(1)
        self.body.addWidget(self.value)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class Banner(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Banner")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        self.icon = QLabel()
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.text, 1)
        self.hide()

    def show_message(self, level: str, text: str) -> None:
        if not text:
            self.hide()
            return
        self.setProperty("level", level)
        name, color = {"ok": ("check", theme.SUCCESS), "warning": ("alert", theme.WARNING)}.get(level, ("alert", theme.DANGER))
        self.icon.setPixmap(icon(name, color, 18).pixmap(18, 18))
        self.text.setText(text)
        self.style().unpolish(self)
        self.style().polish(self)
        self.show()


class MoneyEdit(QLineEdit):
    """Amount input that accepts digits with optional cents and shows thousands separators."""

    value_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setPlaceholderText("0.00")
        self.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9,]{0,15}(\.[0-9]{0,2})?$"), self))
        self.textEdited.connect(lambda _t: self.value_changed.emit())

    def value(self) -> Decimal:
        try:
            return to_decimal(self.text())
        except MoneyError:
            return Decimal(0)

    def set_value(self, value: Decimal | None) -> None:
        self.setText(format_money(value, blank_zero=True) if value is not None else "")

    def focusOutEvent(self, event):  # noqa: N802 (Qt API)
        if self.text():
            self.setText(format_money(self.value(), blank_zero=True))
        super().focusOutEvent(event)


def chip(text: str, kind: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("chip", kind)
    return lbl


def set_chip(lbl: QLabel, text: str, kind: str) -> None:
    lbl.setText(text)
    lbl.setProperty("chip", kind)
    lbl.style().unpolish(lbl)
    lbl.style().polish(lbl)


def section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("SectionTitle")
    return lbl


def set_role(lbl: QLabel, name: str) -> None:
    """Switch a label's style role (objectName) and re-apply the style sheet."""
    if lbl.objectName() != name:
        lbl.setObjectName(name)
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)


def set_flag(widget: QWidget, name: str, on: bool) -> None:
    """Set a true/false style property (e.g. ``negative``) and re-apply the style sheet."""
    if bool(widget.property(name)) != on:
        widget.setProperty(name, on)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    lbl.setWordWrap(True)
    return lbl


def confirm(parent: QWidget, title: str, text: str, ok_text: str = "Continue", danger: bool = False) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
    ok = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is ok


def error(parent: QWidget, text: str, title: str = "Something went wrong") -> None:
    QMessageBox.critical(parent, title, text)


def info(parent: QWidget, text: str, title: str = "Done") -> None:
    QMessageBox.information(parent, title, text)
