"""Monthly renewals: the per-month list sent to UGC."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QSpinBox, QVBoxLayout, QWidget,
)

from ...core.money import format_money
from ...services import exports, renewals
from ...services.errors import ServiceError
from ..dialogs.import_dialog import ImportDialog
from ..icons import icon
from ..widgets.common import Banner, Card, button, chip, confirm, error, info, muted, set_chip
from ..widgets.table import Column, DataTable
from .base import Page


class NewMonthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New renewal month")
        form = QFormLayout(self)
        today = date.today()
        nxt = (today.month % 12) + 1
        self.month = QSpinBox()
        self.month.setRange(1, 12)
        self.month.setValue(nxt)
        self.year = QSpinBox()
        self.year.setRange(2000, 2100)
        self.year.setValue(today.year + (1 if nxt == 1 else 0))
        form.addRow(muted("The month the loans are requested for (LOAN REQUEST MONTH / YEAR)."))
        form.addRow("Request month", self.month)
        form.addRow("Request year", self.year)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class RenewalsPage(Page):
    title = "Monthly Renewals"
    subtitle = "Build each month's renewal list, check it, then export it for UGC"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.batch_id: int | None = None
        self.locked = False

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QVBoxLayout()
        new = button("New month", "plus", "primary")
        new.clicked.connect(self._new_month)
        left.addWidget(new)
        self.months = QListWidget()
        self.months.setFixedWidth(230)
        self.months.currentItemChanged.connect(self._month_selected)
        left.addWidget(self.months, 1)
        body.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(12)
        head = QHBoxLayout()
        self.heading = QLabel("No month selected")
        self.heading.setObjectName("BigNumber")
        self.status = chip("", "draft")
        head.addWidget(self.heading)
        head.addSpacing(10)
        head.addWidget(self.status, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        right.addLayout(head)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.add_btn = button("Add employee", "plus")
        self.add_btn.clicked.connect(self._add_employee)
        self.edit_btn = button("Edit", "edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.remove_btn = button("Remove", "trash", "danger")
        self.remove_btn.clicked.connect(self._remove)
        self.import_btn = button("Import Excel", "upload")
        self.import_btn.clicked.connect(self._import)
        self.lock_btn = button("Finalize", "lock")
        self.lock_btn.clicked.connect(self._toggle_lock)
        self.export_btn = button("Export", "download", "primary")
        menu = QMenu(self)
        menu.addAction(icon("file"), "UGC text file (.txt)", lambda: self._export("text"))
        menu.addAction(icon("report"), "UGC sheet (Excel)", lambda: self._export("excel"))
        menu.addAction(icon("calculator"), "Calculation sheet (Excel)", lambda: self._export("calc"))
        menu.addAction(icon("report"), "Summary (PDF)", lambda: self._export("pdf"))
        self.export_btn.setMenu(menu)
        for b in (self.add_btn, self.edit_btn, self.remove_btn, self.import_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.lock_btn)
        actions.addWidget(self.export_btn)
        right.addLayout(actions)

        self.banner = Banner()
        right.addWidget(self.banner)

        self.table = DataTable([
            Column("#", "pos", "int", width=44), Column("Name", "name", width=220), Column("PF number", "pf", width=96),
            Column("NIC", "nic", width=112), Column("Last loan", "last", width=80),
            Column("Instalment", "instalment", "money", width=100),
            Column("Loan approved", "approved", "money", width=120),
            Column("Existing balance", "existing", "money", width=125),
            Column("Balance payable", "payable", "money", width=125),
            Column("Loan in hand", "in_hand", "money", width=115),
            Column("Flag", "flag", stretch=True, color=lambda r: "#B7791F"),
        ])
        self.table.activated_row.connect(lambda r: self._edit(r["employee_id"]))
        right.addWidget(self.table, 1)

        totals = Card(shadow=False)
        tl = QHBoxLayout()
        self.total_labels: dict[str, QLabel] = {}
        for key, label in (("count", "Employees"), ("loan_approved", "Loans approved"),
                           ("existing_loan_balance", "Existing balances"), ("balance_payable", "Balance payable"),
                           ("loan_in_hand", "Loan in hand")):
            box = QVBoxLayout()
            box.setSpacing(0)
            v = QLabel("0")
            v.setObjectName("StatValue")
            c = QLabel(label)
            c.setObjectName("StatLabel")
            box.addWidget(v)
            box.addWidget(c)
            self.total_labels[key] = v
            tl.addLayout(box)
            tl.addStretch(1)
        totals.body.addLayout(tl)
        right.addWidget(totals)
        body.addLayout(right, 1)
        self.root.addLayout(body, 1)

    # ----- loading
    def refresh(self) -> None:
        keep = self.batch_id
        with self.ctx.db.session() as s:
            items = [(b.id, renewals.batch_label(b), b.status, len(b.entries)) for b in renewals.list_batches(s)]
        self.months.blockSignals(True)
        self.months.clear()
        for bid, label, status, count in items:
            it = QListWidgetItem(icon("lock" if status == "finalized" else "calendar",
                                      "#1E8E5A" if status == "finalized" else "#2F6FED"),
                                 f"{label}\n{count} employee(s) · {status}")
            it.setData(Qt.ItemDataRole.UserRole, bid)
            self.months.addItem(it)
        self.months.blockSignals(False)
        ids = [i[0] for i in items]
        if keep in ids:
            self.months.setCurrentRow(ids.index(keep))
        elif ids:
            self.months.setCurrentRow(0)
        else:
            self.batch_id = None
            self._show_batch()

    def _month_selected(self, item, _prev=None) -> None:
        self.batch_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._show_batch()

    def _show_batch(self) -> None:
        has = self.batch_id is not None
        for b in (self.add_btn, self.edit_btn, self.remove_btn, self.import_btn, self.lock_btn, self.export_btn):
            b.setEnabled(has)
        if not has:
            self.heading.setText("No renewal months yet")
            self.status.hide()
            self.table.set_rows([])
            self.banner.show_message("warning", "Create a month with “New month”, then add employees to it.")
            return
        with self.ctx.db.session() as s:
            batch = renewals.get_batch(s, self.batch_id)
            label, status, self.locked = renewals.batch_label(batch), batch.status, batch.is_locked
            rows = [
                {"employee_id": e.employee_id, "entry_id": e.id, "pos": i, "name": e.employee.name,
                 "pf": e.employee.pf_number, "nic": e.employee.nic,
                 "last": f"{e.last_loan_month:02d}/{e.last_loan_year}" if e.last_loan_month and e.last_loan_year else "",
                 "instalment": e.instalment, "approved": e.loan_approved, "existing": e.existing_loan_balance,
                 "payable": e.balance_payable, "in_hand": e.loan_in_hand,
                 "flag": "< 60%" if e.salary_balance_flag else ""}
                for i, e in enumerate(batch.entries, start=1)
            ]
            t = renewals.totals(batch)
            problems = exports.check_ugc_text(s, self.batch_id) if rows else []
            meta = f"Finalized by {batch.finalized_by} · letter date {batch.letter_date}" if self.locked else ""
        self.heading.setText(label)
        set_chip(self.status, status.title(), status)
        self.status.show()
        self.table.set_rows(rows)
        self.total_labels["count"].setText(str(len(rows)))
        for key in ("loan_approved", "existing_loan_balance", "balance_payable", "loan_in_hand"):
            self.total_labels[key].setText(format_money(t[key]))
        for b in (self.add_btn, self.edit_btn, self.remove_btn, self.import_btn):
            b.setEnabled(not self.locked)
        self.lock_btn.setText("Reopen" if self.locked else "Finalize")
        self.lock_btn.setIcon(icon("unlock" if self.locked else "lock"))
        self.lock_btn.setEnabled(not self.locked or self.ctx.is_admin)
        if not rows:
            self.banner.show_message("warning", "No employees in this month yet. Use “Add employee” or “Import Excel”.")
        elif problems:
            self.banner.show_message("error", "The UGC text file can't be created until these are fixed:\n• "
                                     + "\n• ".join(problems))
        elif self.locked:
            self.banner.show_message("ok", f"Ready for UGC. {meta}")
        else:
            self.banner.show_message("ok", "All rows fit the UGC text format. Finalize the month when it is complete.")

    # ----- actions
    def _new_month(self) -> None:
        dlg = NewMonthDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            with self.ctx.db.session() as s:
                batch = renewals.create_batch(s, self.ctx.user, dlg.month.value(), dlg.year.value())
                self.batch_id = batch.id
        except ServiceError as exc:
            error(self, str(exc))
            return
        self.ctx.events.data_changed.emit("renewals")
        self.refresh()

    def _add_employee(self) -> None:
        self.ctx.events.navigate.emit("calculator", {"batch_id": self.batch_id, "employee_id": None})

    def _edit(self, employee_id: int) -> None:
        if self.locked:
            info(self, "This month is finalized. Reopen it to make changes.", "Finalized")
            return
        self.ctx.events.navigate.emit("calculator", {"batch_id": self.batch_id, "employee_id": employee_id})

    def _edit_selected(self) -> None:
        row = self.table.selected()
        if row:
            self._edit(row["employee_id"])

    def _remove(self) -> None:
        row = self.table.selected()
        if not row:
            return
        if not confirm(self, "Remove employee", f"Remove {row['name']} ({row['pf']}) from this month?\n"
                       "The removal is recorded in the audit log.", "Remove", danger=True):
            return
        try:
            with self.ctx.db.session() as s:
                renewals.remove_entry(s, self.ctx.user, row["entry_id"])
        except ServiceError as exc:
            error(self, str(exc))
        self.ctx.events.data_changed.emit("renewals")
        self.refresh()

    def _import(self) -> None:
        ImportDialog(self.ctx, self.batch_id, self).exec()
        self.refresh()

    def _toggle_lock(self) -> None:
        try:
            if self.locked:
                reason, ok = QInputDialog.getText(self, "Reopen month", "Why does this finalized month need changes?")
                if not ok:
                    return
                with self.ctx.db.session() as s:
                    renewals.reopen(s, self.ctx.user, self.batch_id, reason)
            else:
                letter, ok = QInputDialog.getText(self, "Finalize month",
                                                  "Letter date printed under the signature (dd.mm.yyyy):",
                                                  QLineEdit.EchoMode.Normal, date.today().strftime("%d.%m.%Y"))
                if not ok:
                    return
                if not confirm(self, "Finalize month", "After finalizing, the month can't be edited unless an "
                               "administrator reopens it. Continue?", "Finalize"):
                    return
                with self.ctx.db.session() as s:
                    renewals.finalize(s, self.ctx.user, self.batch_id, letter.strip())
        except ServiceError as exc:
            error(self, str(exc))
            return
        self.ctx.events.data_changed.emit("renewals")
        self.refresh()

    def _export(self, kind: str) -> None:
        export_file(self, self.ctx, self.batch_id, kind)


FILTERS = {"text": "Text file (*.txt)", "excel": "Excel workbook (*.xlsx)", "calc": "Excel workbook (*.xlsx)",
           "pdf": "PDF (*.pdf)"}


def export_file(parent: QWidget, ctx, batch_id: int, kind: str) -> None:
    with ctx.db.session() as s:
        name = exports.default_filename(s, batch_id, kind)
        locked = renewals.get_batch(s, batch_id).is_locked
    if kind in ("text", "excel") and not locked:
        if not confirm(parent, "Month not finalized", "This month is still a draft. Export it anyway?", "Export"):
            return
    path, _ = QFileDialog.getSaveFileName(parent, "Save export", str(Path.home() / name), FILTERS[kind])
    if not path:
        return
    fn = {"text": exports.export_ugc_text, "excel": exports.export_ugc_excel,
          "calc": exports.export_calculation_excel, "pdf": exports.export_pdf}[kind]
    try:
        with ctx.db.session() as s:
            fn(s, ctx.user, batch_id, Path(path))
    except (ServiceError, OSError) as exc:
        error(parent, str(exc), "Export failed")
        return
    info(parent, f"Saved {Path(path).name}.", "Export finished")
