from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QFileDialog, QLineEdit

from ...reports.employee_excel import write_employee_workbook
from ...services import audit, employees
from ...services.errors import ServiceError
from ..dialogs.employee_form import EmployeeDialog
from ..dialogs.import_dialog import ImportDialog
from ..icons import icon
from ..widgets.common import button, error, info
from ..widgets.table import Column, DataTable
from .base import Page


class EmployeesPage(Page):
    title = "Employees"
    subtitle = "Employee records used for PF loan calculations"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name, PF number or NIC")
        self.search.addAction(icon("search", "#6B778C"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(320)
        self.search.textChanged.connect(lambda t: self.table.set_filter(t))
        self.show_inactive = QCheckBox("Show inactive")
        self.show_inactive.toggled.connect(lambda _c: self.refresh())
        self.toolbar.addWidget(self.search)
        self.toolbar.addWidget(self.show_inactive)
        self.toolbar.addStretch(1)
        imp = button("Import Excel", "upload")
        imp.clicked.connect(self._import)
        exp = button("Export Excel", "download")
        exp.clicked.connect(self._export)
        edit = button("Edit", "edit")
        edit.clicked.connect(self._edit_selected)
        add = button("Add employee", "plus", "primary")
        add.clicked.connect(self._add)
        for b in (imp, exp, edit, add):
            self.toolbar.addWidget(b)

        self.table = DataTable([
            Column("PF number", "pf_number", width=110), Column("Name", "name", stretch=True),
            Column("NIC", "nic", width=130), Column("Department", "department", width=200),
            Column("Category", "category", width=110), Column("Designation", "designation", width=180),
            Column("Status", "status", width=90, color=lambda r: "#C53030" if r["status"] == "Inactive" else "#1E8E5A"),
        ])
        self.table.activated_row.connect(lambda r: self._edit(r["id"]))
        self.root.addWidget(self.table, 1)

    def open_with(self, arg) -> None:
        if isinstance(arg, str):
            self.search.setText(arg)

    def refresh(self) -> None:
        with self.ctx.db.session() as s:
            rows = [
                {"id": e.id, "pf_number": e.pf_number, "name": e.name, "nic": e.nic, "department": e.department,
                 "category": "Academic" if e.category == "A" else "Non-academic", "designation": e.designation,
                 "status": "Active" if e.is_active else "Inactive"}
                for e in employees.search(s, include_inactive=self.show_inactive.isChecked())
            ]
        self.table.set_rows(rows)
        self.table.set_filter(self.search.text())

    def _add(self) -> None:
        EmployeeDialog(self.ctx, None, self).exec()
        self.refresh()

    def _edit(self, employee_id: int) -> None:
        EmployeeDialog(self.ctx, employee_id, self).exec()
        self.refresh()

    def _edit_selected(self) -> None:
        row = self.table.selected()
        if row:
            self._edit(row["id"])

    def _import(self) -> None:
        ImportDialog(self.ctx, None, self).exec()
        self.refresh()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export employees", str(Path.home() / "UPF_employees.xlsx"),
                                              "Excel workbook (*.xlsx)")
        if not path:
            return
        try:
            with self.ctx.db.session() as s:
                write_employee_workbook(Path(path), employees.search(s))
                audit.record(s, self.ctx.operator, "export.employees", "employee", summary=Path(path).name)
        except (ServiceError, OSError) as exc:
            error(self, str(exc))
            return
        info(self, f"Saved {Path(path).name}.")
