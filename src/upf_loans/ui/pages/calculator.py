"""Loan calculator: the MAIN sheet row for one employee, with a live breakdown."""

from __future__ import annotations


import calendar

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
    QVBoxLayout, QWidget,
)
from sqlalchemy import select

from ...core.eligibility import LoanInputs, calculate
from ...core.money import format_money
from ...db.models import Employee, RenewalEntry
from ...services import employees, renewals, settings
from ...services.errors import ServiceError
from ..widgets.common import Banner, Card, MoneyEdit, button, error, muted, section, set_flag, set_role
from .base import Page

INPUT_GROUPS = [
    ("Salary", [("salary", "Salary (C)"), ("salary_balance", "Salary balance (D)")]),
    ("PF balance", [("pf_balance", "PF balance at last statement (E)"),
                    ("contributions_since", "Contributions since then (F)")]),
    ("Existing PF loan", [("loan_balance", "PF loan balance at cut-off (H)"),
                          ("loan_deductions_since", "Loan deductions since cut-off (I)")]),
    ("Other university loans", [("distress_loan", "Distress loan (K)"), ("staff_loan", "Staff loan (L)"),
                                ("vehicle_loan", "Vehicle loan (M)"), ("computer_loan", "Computer loan (N)"),
                                ("other_loan_1", "Loan 1 (O)"), ("other_loan_2", "Loan 2 (P)")]),
    ("Q value", [("q_amount", "NTOT_LOBAL / SURETIES (Q)")]),
]


class CalculatorPage(Page):
    title = "Loan Calculator"
    subtitle = "Enter the figures for one employee; results update as you type"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self._employee_ids: list[int] = []
        self._loading = False

        # --- selection bar
        self.employee = QComboBox()
        self.employee.setEditable(True)
        self.employee.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.employee.setMinimumWidth(420)
        self.employee.lineEdit().setPlaceholderText("Type a name, PF number or NIC")
        completer = self.employee.completer()
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.employee.activated.connect(self._employee_chosen)
        self.batch = QComboBox()
        self.batch.setMinimumWidth(200)
        self.batch.currentIndexChanged.connect(lambda _i: self._load_existing())
        self.toolbar.addWidget(QLabel("Employee"))
        self.toolbar.addWidget(self.employee, 1)
        self.toolbar.addSpacing(12)
        self.toolbar.addWidget(QLabel("Renewal month"))
        self.toolbar.addWidget(self.batch)

        body = QHBoxLayout()
        body.setSpacing(16)

        # --- inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner.setObjectName("Workspace")
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 6, 0)
        card = Card("Figures you enter")
        self.inputs: dict[str, MoneyEdit] = {}
        for group, fields in INPUT_GROUPS:
            card.body.addWidget(section(group))
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(6)
            for i, (key, label) in enumerate(fields):
                edit = MoneyEdit()
                edit.value_changed.connect(self._recalc)
                self.inputs[key] = edit
                lbl = QLabel(label)
                lbl.setObjectName("Muted")
                grid.addWidget(lbl, (i // 2) * 2, i % 2)
                grid.addWidget(edit, (i // 2) * 2 + 1, i % 2)
            card.body.addLayout(grid)
        card.body.addWidget(section("Last loan"))
        last = QGridLayout()
        last.setHorizontalSpacing(14)
        last.setVerticalSpacing(6)
        self.last_month = QComboBox()
        self.last_month.addItem("None", 0)
        for m in range(1, 13):
            self.last_month.addItem(f"{m:02d} · {calendar.month_name[m]}", m)
        self.last_year = QLineEdit()
        self.last_year.setPlaceholderText("YYYY")
        self.last_year.setMaxLength(4)
        self.last_year.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}$"), self))
        for i, (text, widget) in enumerate((("Last loan month", self.last_month), ("Last loan year", self.last_year))):
            lbl = QLabel(text)
            lbl.setObjectName("Muted")
            last.addWidget(lbl, 0, i)
            last.addWidget(widget, 1, i)
        card.body.addLayout(last)
        card.body.addWidget(muted("Filled in from the last finalized month when there is one; you can type or "
                                  "change it here. Leave both empty if the employee has no previous loan."))
        il.addWidget(card)
        il.addStretch(1)
        scroll.setWidget(inner)
        body.addWidget(scroll, 3)

        # --- results
        right = QVBoxLayout()
        right.setSpacing(14)
        res = Card("Result")
        big = QGridLayout()
        self.big: dict[str, QLabel] = {}
        for i, (key, label) in enumerate((("loan_approved", "Loan approved"), ("balance_payable", "Balance payable"),
                                          ("instalment", "Monthly instalment"), ("loan_in_hand", "Loan in hand"))):
            box = QVBoxLayout()
            box.setSpacing(0)
            val = QLabel("0.00")
            val.setObjectName("BigNumber" if i < 2 else "StatValue")
            cap = QLabel(label)
            cap.setObjectName("StatLabel")
            box.addWidget(val)
            box.addWidget(cap)
            self.big[key] = val
            big.addLayout(box, i // 2, i % 2)
        res.body.addLayout(big)
        self.banner = Banner()
        res.body.addWidget(self.banner)
        right.addWidget(res)

        steps = Card("How it was calculated")
        self.steps = QFormLayout()
        self.steps.setVerticalSpacing(6)
        self.step_labels: dict[str, QLabel] = {}
        for key in ("total_pf_balance", "existing_loan_balance", "salary_cap", "salary_balance_cap", "pf_balance_cap",
                    "lowest_cap", "q_deduction", "loan_ability", "instalment", "loan_approved", "balance_payable",
                    "other_loans", "loan_in_hand"):
            lbl = QLabel("0.00")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            name = QLabel(key)
            name.setObjectName("Muted")
            self.step_labels[key] = lbl
            self.steps.addRow(name, lbl)
        steps.body.addLayout(self.steps)
        self.rule_note = muted("")
        steps.body.addWidget(self.rule_note)
        right.addWidget(steps)
        right.addStretch(1)

        actions = QHBoxLayout()
        clear = button("Clear")
        clear.clicked.connect(self._clear)
        self.save_btn = button("Save to renewal month", "save", "primary")
        self.save_btn.clicked.connect(self._save)
        actions.addStretch(1)
        actions.addWidget(clear)
        actions.addWidget(self.save_btn)
        right.addLayout(actions)
        body.addLayout(right, 2)
        self.root.addLayout(body, 1)

    # ----- data
    def refresh(self) -> None:
        current_emp = self._current_employee_id()
        current_batch = self.batch.currentData()
        self._loading = True
        with self.ctx.db.session() as s:
            emps = employees.search(s, include_inactive=False)
            batches = [b for b in renewals.list_batches(s) if not b.is_locked]
            self.rules = settings.loan_rules(s)
            labels = [(b.id, renewals.batch_label(b)) for b in batches]
        self._employee_ids = [e.id for e in emps]
        self.employee.clear()
        for e in emps:
            self.employee.addItem(f"{e.pf_number}  ·  {e.name}  ·  {e.nic}", e.id)
        self.employee.setCurrentIndex(-1)
        if current_emp in self._employee_ids:
            self.employee.setCurrentIndex(self._employee_ids.index(current_emp))
        self.batch.clear()
        self.batch.addItem("Calculate only (don't save)", None)
        for bid, label in labels:
            self.batch.addItem(label, bid)
        idx = self.batch.findData(current_batch)
        self.batch.setCurrentIndex(idx if idx >= 0 else (1 if labels else 0))
        self._loading = False
        r = self.rules
        self.rule_note.setText(
            f"Rules: lowest of salary × {r.salary_multiplier}, salary balance × {r.salary_balance_multiplier}, "
            f"PF balance × {r.pf_balance_ratio}; Q above {r.surety_allowance_ratio} × PF balance is deducted; "
            f"instalment rounded down over {r.instalment_months} months. Change these in Settings."
        )
        self._rename_steps()
        self._recalc()

    def _rename_steps(self) -> None:
        r = self.rules
        names = {
            "total_pf_balance": "PF balance (E + F)", "existing_loan_balance": "Existing loan balance (H − I)",
            "salary_cap": f"Salary × {r.salary_multiplier}", "salary_balance_cap": f"Salary balance × {r.salary_balance_multiplier}",
            "pf_balance_cap": f"PF balance × {r.pf_balance_ratio}", "lowest_cap": "Lowest of the three",
            "q_deduction": f"Less Q above {r.surety_allowance_ratio} × PF balance", "loan_ability": "Loan ability",
            "instalment": f"Instalment (rounded down, ÷ {r.instalment_months})",
            "loan_approved": f"Loan approved (instalment × {r.instalment_months})",
            "balance_payable": "Balance payable (approved − existing)", "other_loans": "Less other university loans",
            "loan_in_hand": "Loan in hand",
        }
        for i in range(self.steps.rowCount()):
            label = self.steps.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            key = list(self.step_labels)[i]
            label.setText(names[key])

    def open_with(self, arg) -> None:
        """arg = {"batch_id": ..., "employee_id": ...}"""
        if not isinstance(arg, dict):
            return
        self.refresh()
        idx = self.batch.findData(arg.get("batch_id"))
        if idx >= 0:
            self.batch.setCurrentIndex(idx)
        emp = arg.get("employee_id")
        if emp in self._employee_ids:
            self.employee.setCurrentIndex(self._employee_ids.index(emp))
            self._employee_chosen()
        else:
            self._clear()

    def _current_employee_id(self) -> int | None:
        idx = self.employee.currentIndex()
        if idx < 0 or self.employee.currentText() != self.employee.itemText(idx):
            return None
        return self.employee.itemData(idx)

    def _employee_chosen(self, *_args) -> None:
        self._load_existing()

    def _load_existing(self) -> None:
        if self._loading:
            return
        emp_id = self._current_employee_id()
        if emp_id is None:
            return
        batch_id = self.batch.currentData()
        with self.ctx.db.session() as s:
            batch = s.get(renewals.RenewalBatch, batch_id) if batch_id else None
            entry = None
            if batch is not None:
                entry = s.scalar(select(RenewalEntry).where(RenewalEntry.batch_id == batch.id,
                                                            RenewalEntry.employee_id == emp_id))
            source = entry or renewals.previous_entry(s, emp_id, batch)
            values = {k: getattr(source, k) for k in RenewalEntry.INPUT_FIELDS} if source else {}
            if entry:
                last = (entry.last_loan_month, entry.last_loan_year)
                status = "This employee is already in the selected month; saving updates that row."
            else:
                last = renewals.suggested_last_loan(s, emp_id, batch)
                status = "Pre-filled from this employee's previous month; check every figure." if source else ""
        self._loading = True
        for key, edit in self.inputs.items():
            edit.set_value(values.get(key) if values else None)
        self._set_last_loan(*last)
        self._loading = False
        self._status_note = status
        self._recalc()

    def _set_last_loan(self, month: int | None, year: int | None) -> None:
        self.last_month.setCurrentIndex(max(0, self.last_month.findData(month or 0)))
        self.last_year.setText(str(year) if year else "")

    def _last_loan(self) -> tuple[int | None, int | None]:
        month = self.last_month.currentData() or None
        text = self.last_year.text().strip()
        return month, (int(text) if text else None)

    def _inputs(self) -> LoanInputs:
        return LoanInputs(**{k: e.value() for k, e in self.inputs.items()})

    def _recalc(self) -> None:
        if self._loading or not hasattr(self, "rules"):
            return
        inputs = self._inputs()
        r = calculate(inputs, self.rules)
        for key in ("loan_approved", "balance_payable", "instalment", "loan_in_hand"):
            value = getattr(r, key)
            self.big[key].setText(format_money(value))
            set_flag(self.big[key], "negative", value < 0)
        values = {**{k: getattr(r, k) for k in self.step_labels if hasattr(r, k)},
                  "other_loans": inputs.other_loans_total}
        for key, lbl in self.step_labels.items():
            v = values[key]
            neg = key in ("q_deduction", "other_loans")
            lbl.setText(("− " if neg and v else "") + format_money(v))
        bold = {"lowest_cap", "loan_approved", "balance_payable", "loan_in_hand"}
        limiting = {"salary": "salary_cap", "salary_balance": "salary_balance_cap",
                    "pf_balance": "pf_balance_cap"}[r.limiting_cap]
        for key, lbl in self.step_labels.items():
            set_role(lbl, "Highlight" if key == limiting else ("Strong" if key in bold else "Amount"))
        msgs = list(r.warnings)
        note = getattr(self, "_status_note", "")
        if any(e.value() for e in self.inputs.values()):
            if msgs:
                self.banner.show_message("warning", "\n".join(msgs + ([note] if note else [])))
            else:
                self.banner.show_message("ok", note or "Figures look consistent.")
        else:
            self.banner.show_message("ok", note) if note else self.banner.hide()

    def _clear(self) -> None:
        self._loading = True
        for e in self.inputs.values():
            e.clear()
        self._set_last_loan(None, None)
        self.employee.setCurrentIndex(-1)
        self.employee.setEditText("")
        self._loading = False
        self._status_note = ""
        self._recalc()

    def _save(self) -> None:
        emp_id = self._current_employee_id()
        batch_id = self.batch.currentData()
        if emp_id is None:
            error(self, "Choose an employee from the list first.", "No employee")
            return
        if batch_id is None:
            error(self, "Choose the renewal month to save into, or create one on the Monthly Renewals page.",
                  "No renewal month")
            return
        month, year = self._last_loan()
        if (month is None) != (year is None):
            error(self, "Enter both the last loan month and year, or neither.", "Last loan")
            return
        if year is not None and not 1990 <= year <= 2100:
            error(self, "The last loan year should be four digits, for example 2024.", "Last loan")
            return
        try:
            with self.ctx.db.session() as s:
                entry, result = renewals.save_entry(s, self.ctx.operator, batch_id, emp_id, self._inputs(), month, year)
                name = s.get(Employee, emp_id).name
        except ServiceError as exc:
            error(self, str(exc))
            return
        self.ctx.events.data_changed.emit("renewals")
        self.banner.show_message("ok", f"Saved {name}: loan {format_money(result.loan_approved)}, "
                                       f"payable {format_money(result.balance_payable)}.")
