"""Add / edit employee dialog with renewal history."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QTabWidget,
    QVBoxLayout, QWidget,
)

from ...core.validation import nic_warning
from ...db.models import Employee
from ...services import employees, renewals
from ...services.errors import ServiceError
from ..context import AppContext
from ..widgets.common import muted
from ..widgets.table import Column, DataTable


class EmployeeDialog(QDialog):
    def __init__(self, ctx: AppContext, employee_id: int | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.employee_id = employee_id
        self.setWindowTitle("Edit employee" if employee_id else "Add employee")
        self.resize(640, 520)

        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        details = QWidget()
        form = QFormLayout(details)
        form.setVerticalSpacing(6)
        self.fields: dict[str, QLineEdit] = {}
        self.errors: dict[str, QLabel] = {}

        def add(key: str, label: str, widget: QWidget) -> None:
            err = QLabel()
            err.setObjectName("FieldError")
            err.hide()
            self.errors[key] = err
            box = QVBoxLayout()
            box.setSpacing(2)
            box.addWidget(widget)
            box.addWidget(err)
            form.addRow(label, box)

        for key, label, maxlen in (("pf_number", "PF number", 8), ("name", "Name", 50), ("nic", "NIC", 12),
                                   ("department", "Department", 100), ("designation", "Designation", 100)):
            edit = QLineEdit()
            edit.setMaxLength(maxlen)
            self.fields[key] = edit
            add(key, label, edit)
        self.fields["pf_number"].setPlaceholderText("e.g. R 001365")
        self.fields["nic"].setPlaceholderText("e.g. 680410054V")
        self.fields["nic"].textChanged.connect(self._nic_hint)
        self.category = QComboBox()
        self.category.addItem("Non-academic", "N")
        self.category.addItem("Academic", "A")
        add("category", "Category", self.category)
        self.active = QCheckBox("Active employee")
        self.active.setChecked(True)
        form.addRow("", self.active)
        self.nic_note = muted("")
        form.addRow("", self.nic_note)
        tabs.addTab(details, "Details")

        if employee_id:
            self.history = DataTable([
                Column("Month", "month", width=120), Column("Status", "status", width=90),
                Column("Loan approved", "loan", "money", width=130), Column("Existing balance", "existing", "money", width=130),
                Column("Payable", "payable", "money", stretch=True),
            ])
            tabs.addTab(self.history, "Renewal history")
            self._load()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("variant", "primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _nic_hint(self, text: str) -> None:
        self.nic_note.setText(nic_warning(text.strip().upper()) or "")

    def _load(self) -> None:
        with self.ctx.db.session() as s:
            emp = s.get(Employee, self.employee_id)
            for key, edit in self.fields.items():
                edit.setText(getattr(emp, key) or "")
            self.category.setCurrentIndex(1 if emp.category == "A" else 0)
            self.active.setChecked(emp.is_active)
            rows = [
                {"month": renewals.batch_label(e.batch), "status": e.batch.status.title(), "loan": e.loan_approved,
                 "existing": e.existing_loan_balance, "payable": e.balance_payable}
                for e in employees.history(s, self.employee_id)
            ]
        self.history.set_rows(rows)

    def _data(self) -> employees.EmployeeData:
        return employees.EmployeeData(
            **{k: e.text() for k, e in self.fields.items()},
            category=self.category.currentData(), is_active=self.active.isChecked(),
        )

    def _save(self) -> None:
        for err in self.errors.values():
            err.hide()
        data = self._data().cleaned()
        try:
            with self.ctx.db.session() as s:
                errs = employees.validate(s, data, self.employee_id)
                if errs:
                    for key, msg in errs.items():
                        self.errors[key].setText(msg)
                        self.errors[key].show()
                    return
                dup = employees.duplicate_nic(s, data.nic, self.employee_id)
                if dup:
                    from ..widgets.common import confirm
                    if not confirm(self, "Duplicate NIC", f"{dup.name} ({dup.pf_number}) already has NIC {data.nic}.\n"
                                   "Save anyway? (One person can hold two PF numbers.)"):
                        return
                emp = employees.save(s, self.ctx.user, data, self.employee_id)
                self.employee_id = emp.id
        except ServiceError as exc:
            from ..widgets.common import error
            error(self, str(exc))
            return
        self.ctx.events.data_changed.emit("employees")
        self.accept()
