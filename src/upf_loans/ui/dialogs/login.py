"""Login and first-run administrator setup."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from ...config import APP_NAME, APP_VERSION
from ...db.models import User
from ...db.session import Database
from ...services import auth
from ...services.errors import ServiceError
from ..icons import icon
from ..widgets.common import button


class LoginDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None):
        super().__init__(parent)
        self.db = db
        self.user: User | None = None
        with db.session() as s:
            self.first_run = not auth.has_users(s)
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(780, 460)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        brand = QFrame()
        brand.setObjectName("LoginPanel")
        brand.setFixedWidth(320)
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(32, 36, 32, 28)
        logo = QLabel()
        logo.setPixmap(icon("wallet", "#FFFFFF", 40).pixmap(40, 40))
        title = QLabel("UPF Loan\nManager")
        title.setStyleSheet("font-size:22pt;font-weight:600;")
        sub = QLabel("University Provident Fund loan renewals, calculations and UGC submissions.")
        sub.setObjectName("LoginSub")
        sub.setWordWrap(True)
        ver = QLabel(f"Version {APP_VERSION} · works offline")
        ver.setObjectName("LoginSub")
        bl.addWidget(logo)
        bl.addSpacing(14)
        bl.addWidget(title)
        bl.addSpacing(8)
        bl.addWidget(sub)
        bl.addStretch(1)
        bl.addWidget(ver)
        root.addWidget(brand)

        form_wrap = QWidget()
        fl = QVBoxLayout(form_wrap)
        fl.setContentsMargins(44, 44, 44, 36)
        heading = QLabel("Create the administrator account" if self.first_run else "Sign in")
        heading.setStyleSheet("font-size:16pt;font-weight:600;")
        hint = QLabel(
            "This is the first start. The account you create here can manage users and settings."
            if self.first_run else "Use your UPF Loan Manager account."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        fl.addWidget(heading)
        fl.addWidget(hint)
        fl.addSpacing(16)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.full_name = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        if self.first_run:
            form.addRow("Full name", self.full_name)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        if self.first_run:
            form.addRow("Confirm password", self.confirm)
        fl.addLayout(form)
        self.error = QLabel()
        self.error.setObjectName("FieldError")
        self.error.setWordWrap(True)
        fl.addWidget(self.error)
        fl.addStretch(1)
        self.submit = button("Create account" if self.first_run else "Sign in", variant="primary")
        self.submit.setDefault(True)
        self.submit.clicked.connect(self._submit)
        fl.addWidget(self.submit)
        root.addWidget(form_wrap, 1)
        self.username.setFocus()

    def _submit(self) -> None:
        self.error.clear()
        username, password = self.username.text().strip(), self.password.text()
        if not username or not password:
            self.error.setText("Enter a username and password.")
            return
        try:
            with self.db.session() as s:
                if self.first_run:
                    if password != self.confirm.text():
                        self.error.setText("The passwords do not match.")
                        return
                    auth.create_user(s, None, username, password, self.full_name.text(), "admin")
                user = auth.authenticate(s, username, password)
        except ServiceError as exc:
            self.error.setText(str(exc))
            return
        if user is None:
            self.error.setText("Wrong username or password.")
            self.password.selectAll()
            self.password.setFocus()
            return
        self.user = user
        self.accept()
