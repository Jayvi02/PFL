from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel
from sqlalchemy import func, select

from ...core.money import format_money
from ...db.models import Employee, RenewalBatch
from ...services import audit, renewals
from ..widgets.common import Card, StatCard, button, chip, muted, set_chip
from ..widgets.table import Column, DataTable
from .base import Page


class DashboardPage(Page):
    title = "Dashboard"
    subtitle = "Track employees and monthly loan renewals"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.toolbar.addStretch(1)
        new_calc = button("New calculation", "calculator", "primary")
        new_calc.clicked.connect(lambda: ctx.events.navigate.emit("calculator", None))
        self.toolbar.addWidget(new_calc)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.cards = {
            "approved": StatCard("Loans approved · latest month (Rs.)", "wallet", accent=True),
            "payable": StatCard("Balance payable · latest month (Rs.)", "report"),
            "employees": StatCard("Active employees", "users"),
            "months": StatCard("Renewal months on record", "calendar"),
        }
        for i, card in enumerate(self.cards.values()):
            card.setMinimumHeight(118)
            grid.addWidget(card, 0, i)
        self.root.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.latest = Card("Latest renewal month")
        head = QHBoxLayout()
        self.latest_label = QLabel("No months yet")
        self.latest_label.setObjectName("Hero")
        self.latest_chip = chip("", "draft")
        head.addWidget(self.latest_label)
        head.addSpacing(8)
        head.addWidget(self.latest_chip)
        head.addStretch(1)
        self.latest.body.addLayout(head)
        self.latest_detail = muted("")
        self.latest.body.addWidget(self.latest_detail)
        self.latest.body.addStretch(1)
        go = button("Open monthly renewals", "arrow-up-right")
        go.clicked.connect(lambda: ctx.events.navigate.emit("renewals", None))
        self.latest.body.addWidget(go)
        row.addWidget(self.latest, 2)

        activity = Card("Recent activity")
        self.activity = DataTable([
            Column("When", "when", width=150), Column("By", "user", width=110), Column("What", "what", stretch=True),
        ])
        activity.body.addWidget(self.activity)
        row.addWidget(activity, 3)
        self.root.addLayout(row, 1)

    def refresh(self) -> None:
        with self.ctx.db.session() as s:
            active = s.scalar(select(func.count(Employee.id)).where(Employee.is_active.is_(True))) or 0
            months = s.scalar(select(func.count(RenewalBatch.id))) or 0
            batches = renewals.list_batches(s)
            latest = batches[0] if batches else None
            if latest:
                t = renewals.totals(latest)
                count = len(latest.entries)
                label, status = renewals.batch_label(latest), latest.status
            logs = [
                {"when": a.created_at.strftime("%d %b %Y %H:%M") if a.created_at else "", "user": a.username,
                 "what": f"{a.action.replace('.', ' ')}: {a.summary}".strip(": ")}
                for a in audit.recent(s, 40)
            ]
        self.cards["employees"].set_value(f"{active:,}")
        self.cards["months"].set_value(f"{months:,}")
        if latest:
            self.cards["approved"].set_value(format_money(t["loan_approved"]))
            self.cards["payable"].set_value(format_money(t["balance_payable"]))
            self.latest_label.setText(label)
            set_chip(self.latest_chip, status.title(), status)
            self.latest_chip.show()
            self.latest_detail.setText(
                f"{count} employee(s)\nExisting balances {format_money(t['existing_loan_balance'])}\n"
                f"Loan in hand {format_money(t['loan_in_hand'])}"
            )
        else:
            for key in ("approved", "payable"):
                self.cards[key].set_value(format_money(Decimal(0)))
            self.latest_chip.hide()
            self.latest_detail.setText("Create a renewal month to start calculating loans.")
        self.activity.set_rows(logs)
