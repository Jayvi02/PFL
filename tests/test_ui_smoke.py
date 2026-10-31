"""Smoke test: every page builds and the main flow works with no dialogs."""

from decimal import Decimal as D

import pytest

pytest.importorskip("PySide6")

from upf_loans.core.eligibility import LoanInputs  # noqa: E402
from upf_loans.services import employees, renewals  # noqa: E402


def test_main_window_pages(qtbot, db, admin):
    from upf_loans.ui.context import AppContext, Events
    from upf_loans.ui.main_window import MainWindow

    with db.session() as s:
        emp = employees.save(s, admin, employees.EmployeeData("R 001365", "Perera A.", "680410054V"))
        b = renewals.create_batch(s, admin, 11, 2024)
        renewals.save_entry(s, admin, b.id, emp.id, LoanInputs(salary=D(72791), salary_balance=D(26455),
                            pf_balance=D("3622669.53"), contributions_since=D("105650.79"),
                            loan_balance=D(1760970), loan_deductions_since=D(150500)), 10, 2023)
        emp_id, batch_id = emp.id, b.id
    ctx = AppContext(db=db, user=admin, events=Events())
    win = MainWindow(ctx)
    qtbot.addWidget(win)
    win.show()
    for key in ("dashboard", "employees", "calculator", "renewals", "reports", "settings"):
        win.show_page(key)
    assert win.pages["employees"].table.model_.rowCount() == 1
    assert win.pages["renewals"].table.model_.rowCount() == 1
    calc = win.pages["calculator"]
    win.show_page("calculator", {"batch_id": batch_id, "employee_id": emp_id})
    assert calc.big["loan_approved"].text() == "2,423,400.00"
    assert calc.big["balance_payable"].text() == "812,930.00"
    calc.inputs["vehicle_loan"].setText("30000")
    calc.inputs["vehicle_loan"].value_changed.emit()
    assert calc.big["loan_in_hand"].text() == "782,930.00"
