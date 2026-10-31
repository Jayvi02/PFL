"""Main window: fixed left sidebar, header with search, page stack."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from ..config import APP_NAME, APP_VERSION
from .context import AppContext
from .icons import icon
from .pages.calculator import CalculatorPage
from .pages.dashboard import DashboardPage
from .pages.employees import EmployeesPage
from .pages.renewals import RenewalsPage
from .pages.reports import ReportsPage
from .pages.settings import SettingsPage

NAV = [
    ("dashboard", "Dashboard", "dashboard", DashboardPage),
    ("employees", "Employees", "users", EmployeesPage),
    ("calculator", "Loan Calculator", "calculator", CalculatorPage),
    ("renewals", "Monthly Renewals", "renew", RenewalsPage),
    ("reports", "Reports", "report", ReportsPage),
    ("settings", "Settings", "settings", SettingsPage),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 840)
        self.setMinimumSize(1100, 680)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 20, 14, 16)
        sl.setSpacing(4)
        brand_row = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icon("wallet", "#FFFFFF", 26).pixmap(26, 26))
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        b1 = QLabel("UPF Loan Manager")
        b1.setObjectName("Brand")
        b2 = QLabel("Provident Fund loans")
        b2.setObjectName("BrandSub")
        brand_text.addWidget(b1)
        brand_text.addWidget(b2)
        brand_row.addWidget(logo)
        brand_row.addSpacing(4)
        brand_row.addLayout(brand_text, 1)
        sl.addLayout(brand_row)
        sl.addSpacing(22)

        self.stack = QStackedWidget()
        self.pages: dict[str, object] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, label, icon_name, cls in NAV:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setIcon(icon(icon_name, "#D6E0F2"))
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, k=key: self.show_page(k))
            group.addButton(btn)
            sl.addWidget(btn)
            self.nav_buttons[key] = btn
            page = cls(ctx)
            self.pages[key] = page
            self.stack.addWidget(page)
        sl.addStretch(1)
        ver = QLabel(f"v{APP_VERSION} · offline")
        ver.setObjectName("Version")
        sl.addWidget(ver)
        root.addWidget(side)

        # Header + workspace
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(76)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 10, 20, 10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_sub = QLabel()
        self.page_sub.setObjectName("Muted")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_sub)
        hl.addLayout(titles, 1)
        self.search = QLineEdit()
        self.search.setObjectName("GlobalSearch")
        self.search.setPlaceholderText("Find employee by name, PF number or NIC")
        self.search.addAction(icon("search", "#6B778C"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.returnPressed.connect(self._global_search)
        hl.addWidget(self.search)
        hl.addSpacing(16)
        main.addWidget(header)
        main.addWidget(self.stack, 1)
        root.addLayout(main, 1)
        self.setCentralWidget(central)

        ctx.events.navigate.connect(self.show_page)
        self.show_page("dashboard")

    def show_page(self, key: str, arg=None) -> None:
        page = self.pages[key]
        self.nav_buttons[key].setChecked(True)
        self.page_title.setText(page.title)
        self.page_sub.setText(page.subtitle)
        self.stack.setCurrentWidget(page)
        if arg is not None:
            page.open_with(arg)

    def _global_search(self) -> None:
        text = self.search.text().strip()
        self.show_page("employees", text)
        self.search.clear()
