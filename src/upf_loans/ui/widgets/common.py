"""Reusable widgets: cards, stat tiles, money input, banners, dialogs."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)
from PySide6.QtGui import QColor

from ...core.money import MoneyError, format_money, to_decimal
from ..icons import icon


def button(text: str, icon_name: str | None = None, variant: str | None = None, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    if icon_name:
        color = "#FFFFFF" if variant == "primary" else ("#C53030" if variant == "danger" else "#1F3A68")
        btn.setIcon(icon(icon_name, color))
    if variant:
        btn.setProperty("variant", variant)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class Card(QFrame):
    def __init__(self, title: str | None = None, parent: QWidget | None = None, shadow: bool = True):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("CardTitle")
            self.body.addWidget(lbl)
        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(18)
            effect.setOffset(0, 2)
            effect.setColor(QColor(31, 58, 104, 22))
            self.setGraphicsEffect(effect)


class StatCard(Card):
    def __init__(self, label: str, icon_name: str, parent: QWidget | None = None):
        super().__init__(parent=parent)
        row = QHBoxLayout()
        badge = QLabel()
        badge.setPixmap(icon(icon_name, "#2F6FED", 22).pixmap(22, 22))
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("background:#E8F0FE;border-radius:10px;")
        text = QVBoxLayout()
        text.setSpacing(0)
        self.value = QLabel("–")
        self.value.setObjectName("StatValue")
        cap = QLabel(label)
        cap.setObjectName("StatLabel")
        text.addWidget(self.value)
        text.addWidget(cap)
        row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        row.addSpacing(6)
        row.addLayout(text, 1)
        self.body.addLayout(row)

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
        name, color = {"ok": ("check", "#1E8E5A"), "warning": ("alert", "#B7791F")}.get(level, ("alert", "#C53030"))
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
    lbl = QLabel(text)
    lbl.setObjectName("SectionTitle")
    return lbl


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
