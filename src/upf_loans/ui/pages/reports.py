from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel

from ...reports.employee_excel import write_employee_workbook
from ...services import audit, employees, renewals
from ..widgets.common import Card, button, error, info, muted
from .base import Page
from .renewals import export_file

EXPORTS = [
    ("text", "UGC text file", "file",
     "The PF LOAN send UGC sheet as a tab-delimited text file: headings, every employee, totals and signature, as Excel saves it."),
    ("excel", "UGC renewal sheet", "report",
     "The “PF LOAN send UGC” sheet: title, 12 columns, totals and the Bursar signature block, landscape A4."),
    ("calc", "Calculation sheet", "calculator",
     "Every figure entered and calculated for the month, in the MAIN sheet layout with live Excel formulas."),
    ("pdf", "Summary PDF", "report", "A printable summary of the month with totals."),
]


class ReportsPage(Page):
    title = "Reports"
    subtitle = "Exports for UGC and for your records"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.toolbar.addWidget(QLabel("Renewal month"))
        self.batch = QComboBox()
        self.batch.setMinimumWidth(220)
        self.toolbar.addWidget(self.batch)
        self.toolbar.addStretch(1)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.buttons = []
        for i, (kind, title, icon_name, text) in enumerate(EXPORTS):
            card = Card(title)
            card.body.addWidget(muted(text))
            card.body.addStretch(1)
            row = QHBoxLayout()
            row.addStretch(1)
            b = button("Export", icon_name, "primary")
            b.clicked.connect(lambda _c=False, k=kind: self._export(k))
            self.buttons.append(b)
            row.addWidget(b)
            card.body.addLayout(row)
            grid.addWidget(card, i // 2, i % 2)
        emp = Card("Employee list")
        emp.body.addWidget(muted("All employee records as an Excel workbook with filters."))
        emp.body.addStretch(1)
        eb = button("Export", "download")
        eb.clicked.connect(self._export_employees)
        r = QHBoxLayout()
        r.addStretch(1)
        r.addWidget(eb)
        emp.body.addLayout(r)
        grid.addWidget(emp, 2, 0)
        self.root.addLayout(grid)
        self.root.addStretch(1)

    def refresh(self) -> None:
        current = self.batch.currentData()
        with self.ctx.db.session() as s:
            items = [(b.id, f"{renewals.batch_label(b)} ({b.status})") for b in renewals.list_batches(s)]
        self.batch.clear()
        for bid, label in items:
            self.batch.addItem(label, bid)
        idx = self.batch.findData(current)
        if idx >= 0:
            self.batch.setCurrentIndex(idx)
        for b in self.buttons:
            b.setEnabled(bool(items))

    def _export(self, kind: str) -> None:
        if self.batch.currentData() is not None:
            export_file(self, self.ctx, self.batch.currentData(), kind)

    def _export_employees(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export employees", str(Path.home() / "UPF_employees.xlsx"),
                                              "Excel workbook (*.xlsx)")
        if not path:
            return
        try:
            with self.ctx.db.session() as s:
                write_employee_workbook(Path(path), employees.search(s))
                audit.record(s, self.ctx.operator, "export.employees", "employee", summary=Path(path).name)
        except OSError as exc:
            error(self, str(exc))
            return
        info(self, f"Saved {Path(path).name}.")
