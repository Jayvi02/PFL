"""Sortable, filterable table built on a simple row model."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from ...core.money import format_money
from .. import theme


@dataclass
class Column:
    title: str
    key: str
    kind: str = "text"  # text | money | int
    width: int | None = None
    stretch: bool = False
    color: Callable[[dict], str | None] | None = None


class RowModel(QAbstractTableModel):
    def __init__(self, columns: list[Column]):
        super().__init__()
        self.columns = columns
        self.rows: list[dict] = []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.columns[section].title
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.TextAlignmentRole:
            col = self.columns[section]
            return int((Qt.AlignmentFlag.AlignRight if col.kind != "text" else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        col = self.columns[index.column()]
        value: Any = row.get(col.key)
        if role == Qt.ItemDataRole.DisplayRole:
            if col.kind == "money":
                return format_money(value) if value is not None else ""
            return "" if value is None else str(value)
        if role == Qt.ItemDataRole.UserRole:  # sort key
            if col.kind in ("money", "int"):
                return float(value) if isinstance(value, (int, float, Decimal)) else 0.0
            return "" if value is None else str(value).lower()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col.kind != "text":
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if col.color:
                color = col.color(row)
                if color:
                    return QColor(color)
            if col.kind == "money" and isinstance(value, Decimal) and value < 0:
                return QColor(theme.DANGER)
        if role == Qt.ItemDataRole.ToolTipRole:
            return row.get("_tooltip")
        return None


class FilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.setSortRole(Qt.ItemDataRole.UserRole)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)


class DataTable(QTableView):
    activated_row = Signal(dict)

    def __init__(self, columns: list[Column], parent=None):
        super().__init__(parent)
        self.model_ = RowModel(columns)
        self.proxy = FilterProxy()
        self.proxy.setSourceModel(self.model_)
        self.setModel(self.proxy)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.proxy.sort(-1)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(34)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionsMovable(True)
        header.setStretchLastSection(False)
        for i, col in enumerate(columns):
            if col.stretch:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(i, col.width or 120)
        self.doubleClicked.connect(self._on_double)

    def set_rows(self, rows: list[dict]) -> None:
        self.model_.set_rows(rows)

    def set_filter(self, text: str) -> None:
        self.proxy.setFilterFixedString(text)

    def selected(self) -> dict | None:
        idx = self.selectionModel().selectedRows()
        if not idx:
            return None
        return self.model_.rows[self.proxy.mapToSource(idx[0]).row()]

    def _on_double(self, index):
        self.activated_row.emit(self.model_.rows[self.proxy.mapToSource(index).row()])
