"""Rounded "pill" bar chart for monthly totals (the latest month is lit in lime)."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import theme


def _short(value: Decimal) -> str:
    v = float(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= limit:
            return f"{v / limit:.1f}{suffix}"
    return f"{v:,.0f}"


class PillChart(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.items: list[tuple[str, Decimal]] = []
        self.progress = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(700)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._step)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_items(self, items: list[tuple[str, Decimal]]) -> None:
        if items == self.items:
            return
        self.items = items
        self._anim.stop()
        self._anim.start()  # bars grow up from the bottom

    def _step(self, value) -> None:
        self.progress = float(value)
        self.update()

    def paintEvent(self, _event):  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if not self.items:
            p.setPen(QColor(theme.MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Totals appear here once you have renewal months.")
            p.end()
            return
        label_h = 22
        top = 6
        bar_area = h - label_h - top
        n = len(self.items)
        gap = 14
        bar_w = min(58.0, (w - gap * (n - 1)) / n)
        total_w = bar_w * n + gap * (n - 1)
        x = (w - total_w) / 2
        peak = max((float(v) for _, v in self.items), default=0) or 1.0
        value_font = QFont(self.font())
        value_font.setFamilies(["Cascadia Mono", "JetBrains Mono", "Consolas", "DejaVu Sans Mono"])
        value_font.setPointSizeF(8.5)
        value_font.setBold(True)
        label_font = QFont(self.font())
        label_font.setPointSizeF(8.5)
        for i, (label, value) in enumerate(self.items):
            last = i == n - 1
            track = QRectF(x, top, bar_w, bar_area)
            path = QPainterPath()
            path.addRoundedRect(track, bar_w / 2, bar_w / 2)
            p.fillPath(path, QColor(255, 255, 255, 14))
            p.setPen(QPen(QColor(255, 255, 255, 22), 1))
            p.drawPath(path)
            frac = max(0.0, float(value)) / peak * self.progress
            fill_h = max(bar_w, bar_area * frac)
            fill = QRectF(x, top + bar_area - fill_h, bar_w, fill_h)
            fpath = QPainterPath()
            fpath.addRoundedRect(fill, bar_w / 2, bar_w / 2)
            p.fillPath(fpath, QColor(theme.LIME) if last else QColor(255, 255, 255, 46))
            # value, written upwards inside the bar
            p.save()
            p.setFont(value_font)
            p.setPen(QColor(theme.ON_LIME) if last else QColor(theme.TEXT))
            p.translate(x + bar_w / 2, top + bar_area - 12)
            p.rotate(-90)
            p.drawText(QRectF(0, -10, bar_area - 20, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       _short(value))
            p.restore()
            p.setFont(label_font)
            p.setPen(QColor(theme.TEXT) if last else QColor(theme.MUTED))
            p.drawText(QRectF(x - gap / 2, h - label_h, bar_w + gap, label_h), Qt.AlignmentFlag.AlignCenter, label)
            x += bar_w + gap
        p.end()
