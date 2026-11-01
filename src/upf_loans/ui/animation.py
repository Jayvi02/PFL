"""Small, quick animations: page fade-in, sliding nav highlight, counting numbers.

Everything is short (under half a second) and finishes in a plain, effect-free
state, so tables and inputs render normally once an animation ends.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

EASE = QEasingCurve.Type.OutCubic


def fade_in(widget: QWidget, duration: int = 260) -> None:
    """Fade a page in, then remove the effect (graphics effects slow big tables)."""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(EASE)
    widget._fade_anim = anim  # keep a reference until it ends

    def done() -> None:
        # Remove the effect after the animation has fully unwound, never from inside its own signal.
        def clear() -> None:
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
        QTimer.singleShot(0, widget, clear)

    anim.finished.connect(done)
    anim.start()


def slide_to(widget: QWidget, target: QRect, duration: int = 280) -> None:
    """Glide a widget to a new geometry (the sidebar's lime highlight)."""
    old = getattr(widget, "_slide_anim", None)
    if old is not None:
        old.stop()
    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setDuration(duration)
    anim.setStartValue(widget.geometry())
    anim.setEndValue(target)
    anim.setEasingCurve(EASE)
    widget._slide_anim = anim
    anim.start()


_NUMBER = re.compile(r"^-?[\d,]+(\.\d+)?$")


def count_to(label: QLabel, text: str, duration: int = 600) -> None:
    """Show ``text``; when it is a number like 1,234.00, count up to it first."""
    old = getattr(label, "_count_anim", None)
    if old is not None:
        old.stop()
    if text == label.text():
        return
    if not _NUMBER.match(text or ""):
        label.setText(text)
        return
    try:
        target = Decimal(text.replace(",", ""))
    except InvalidOperation:
        label.setText(text)
        return
    decimals = len(text.split(".")[1]) if "." in text else 0
    anim = QVariantAnimation(label)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(float(target))
    anim.setEasingCurve(EASE)
    anim.valueChanged.connect(lambda v: label.setText(f"{v:,.{decimals}f}"))
    anim.finished.connect(lambda: label.setText(text))  # end on the exact figure
    label._count_anim = anim
    anim.start()
