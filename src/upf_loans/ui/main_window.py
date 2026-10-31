"""Main window: floating glass sidebar and a glass shell holding the header and pages."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QStackedWidget,
    QVBoxLayout,
)

from ..config import APP_NAME
from ..services import updater
from . import background, theme
from .context import AppContext
from .icons import icon, toggle_icon
from .pages.calculator import CalculatorPage
from .pages.dashboard import DashboardPage
from .pages.employees import EmployeesPage
from .pages.renewals import RenewalsPage
from .pages.reports import ReportsPage
from .pages.settings import SettingsPage
from .widgets.backdrop import Backdrop
from .widgets.common import button

NAV = [
    ("dashboard", "Dashboard", "dashboard", DashboardPage),
    ("employees", "Employees", "users", EmployeesPage),
    ("calculator", "Loan Calculator", "calculator", CalculatorPage),
    ("renewals", "Monthly Renewals", "renew", RenewalsPage),
    ("reports", "Reports", "report", ReportsPage),
    ("settings", "Settings", "settings", SettingsPage),
]


def version_text() -> tuple[str, str]:
    built = updater.build_date()
    return f"Version {updater.current_version()}", (f"Built {built}" if built else "Running from source")


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)

        central = Backdrop()
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        # ---- Sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(240)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(4)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("Logo")
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(icon("wallet", theme.ON_LIME, 22).pixmap(22, 22))
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        b1 = QLabel("UPF Loans")
        b1.setObjectName("Brand")
        b2 = QLabel("Provident Fund manager")
        b2.setObjectName("BrandSub")
        brand_text.addWidget(b1)
        brand_text.addWidget(b2)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text, 1)
        sl.addLayout(brand_row)
        sl.addSpacing(26)

        self.stack = QStackedWidget()
        self.stack.setObjectName("Workspace")
        self.pages: dict[str, object] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, label, icon_name, cls in NAV:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setIcon(toggle_icon(icon_name, theme.TEXT_SOFT, theme.ON_LIME))
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

        vbox = QFrame()
        vbox.setObjectName("VersionBox")
        vl = QVBoxLayout(vbox)
        vl.setContentsMargins(12, 10, 12, 10)
        vl.setSpacing(2)
        line1, line2 = version_text()
        self.version_label = QLabel(line1)
        self.version_label.setObjectName("Version")
        self.version_date = QLabel(f"{line2} · works offline")
        self.version_date.setObjectName("VersionDate")
        vl.addWidget(self.version_label)
        vl.addWidget(self.version_date)
        sl.addWidget(vbox)
        root.addWidget(side)

        # ---- Shell: header + pages
        shell = QFrame()
        shell.setObjectName("Shell")
        main = QVBoxLayout(shell)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(104)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 18, 24, 6)
        hl.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_sub = QLabel()
        self.page_sub.setObjectName("PageSub")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_sub)
        hl.addLayout(titles, 1)
        self.update_btn = button("Update available", "sparkle", "primary")
        self.update_btn.clicked.connect(lambda: self.show_page("settings", "updates"))
        self.update_btn.hide()
        hl.addWidget(self.update_btn)
        today = QPushButton(date.today().strftime("%a, %d %b %Y"))
        today.setIcon(icon("calendar", theme.TEXT_SOFT))
        today.setProperty("variant", "pill")
        today.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        today.setCursor(Qt.CursorShape.PointingHandCursor)
        today.clicked.connect(lambda: self.show_page("renewals"))
        today.setToolTip("Open monthly renewals")
        hl.addWidget(today)
        self.search = QLineEdit()
        self.search.setObjectName("GlobalSearch")
        self.search.setPlaceholderText("Find employee by name, PF number or NIC")
        self.search.addAction(icon("search", theme.MUTED), QLineEdit.ActionPosition.LeadingPosition)
        self.search.returnPressed.connect(self._global_search)
        hl.addWidget(self.search)
        main.addWidget(header)
        main.addWidget(self.stack, 1)
        root.addWidget(shell, 1)
        self.setCentralWidget(central)

        ctx.events.navigate.connect(self.show_page)
        ctx.events.update_found.connect(lambda _info: self.update_btn.show())
        self.show_page("dashboard")
        if updater.is_installed_build():
            QTimer.singleShot(3000, self._quiet_update_check)

    def _quiet_update_check(self) -> None:
        """Check GitHub once at start-up; stay silent when offline."""
        def done(info):
            if info.available:
                self.ctx.events.update_found.emit(info)
        background.run(updater.check, done, lambda _msg: None)

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
