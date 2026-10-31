"""The softly lit background the glass panels float on."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget


class Backdrop(QWidget):
    # (centre x, centre y as a fraction of the window, radius as a fraction of the diagonal, colour)
    GLOWS = (
        (0.08, 0.05, 0.55, QColor(255, 186, 120, 46)),   # warm window light, top left
        (0.92, 0.95, 0.55, QColor(200, 240, 60, 40)),    # lime glow, bottom right
        (0.70, 0.10, 0.45, QColor(96, 140, 255, 34)),    # cool blue, top right
        (0.25, 0.95, 0.40, QColor(150, 110, 255, 22)),   # violet, bottom left
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Backdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def paintEvent(self, _event):  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        base = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base.setColorAt(0.0, QColor("#1A1C22"))
        base.setColorAt(0.55, QColor("#101217"))
        base.setColorAt(1.0, QColor("#0B0C10"))
        p.fillRect(rect, base)
        diag = (rect.width() ** 2 + rect.height() ** 2) ** 0.5
        for fx, fy, fr, colour in self.GLOWS:
            centre = QPointF(rect.width() * fx, rect.height() * fy)
            g = QRadialGradient(centre, diag * fr)
            g.setColorAt(0.0, colour)
            fade = QColor(colour)
            fade.setAlpha(0)
            g.setColorAt(1.0, fade)
            p.fillRect(rect, g)
        p.end()
