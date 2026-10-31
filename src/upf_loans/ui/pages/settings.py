from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QTabWidget, QVBoxLayout, QWidget,
)

from ... import config
from ...services import audit, auth, backup, settings
from ...services.errors import ServiceError
from ..widgets.common import Banner, Card, button, confirm, error, info, muted
from ..widgets.table import Column, DataTable
from .base import Page

RULE_FIELDS = [
    ("salary_multiplier", "Salary multiplier", "Cap 1: salary × this (Excel column U, default 48)"),
    ("salary_balance_multiplier", "Salary balance multiplier", "Cap 2: salary balance × this (column V, default 120)"),
    ("pf_balance_ratio", "PF balance ratio", "Cap 3: PF balance × this (column W, default 0.65)"),
    ("surety_allowance_ratio", "Q allowance ratio", "Q above PF balance × this is deducted (column Y, default 0.1)"),
    ("instalment_months", "Number of instalments", "Loan = whole instalments × this (columns Z/AA, default 120)"),
]


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add user")
        form = QFormLayout(self)
        self.username = QLineEdit()
        self.full_name = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItem("Officer: employees, calculations, exports", "officer")
        self.role.addItem("Administrator: also settings, users, reopen, restore", "admin")
        form.addRow("Username", self.username)
        form.addRow("Full name", self.full_name)
        form.addRow("Password", self.password)
        form.addRow("Role", self.role)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        form.addRow(b)


class SettingsPage(Page):
    title = "Settings"
    subtitle = "Loan rules, UGC details, users and backups"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.tabs = QTabWidget()
        self.root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._rules_tab(), "Loan rules")
        self.tabs.addTab(self._ugc_tab(), "University && UGC")
        self.tabs.addTab(self._users_tab(), "Users")
        self.tabs.addTab(self._backup_tab(), "Backup && restore")
        self.tabs.addTab(self._audit_tab(), "Audit log")

    # ----- tabs
    def _rules_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = Card("Loan rule values")
        card.body.addWidget(muted(
            "These replace the fixed numbers in the Excel formulas. Changes apply to calculations saved from now on; "
            "rows already saved keep the values they were calculated with."
        ))
        form = QFormLayout()
        self.rule_edits: dict[str, QLineEdit] = {}
        for key, label, hint in RULE_FIELDS:
            edit = QLineEdit()
            edit.setMaximumWidth(160)
            edit.setToolTip(hint)
            self.rule_edits[key] = edit
            box = QHBoxLayout()
            box.setSpacing(12)
            box.addWidget(edit)
            hint_label = muted(hint)
            hint_label.setWordWrap(False)
            box.addWidget(hint_label, 1)
            form.addRow(label, box)
        card.body.addLayout(form)
        row = QHBoxLayout()
        row.addStretch(1)
        reset = button("Restore Excel defaults")
        reset.clicked.connect(self._reset_rules)
        save = button("Save rules", "save", "primary")
        save.clicked.connect(lambda: self._save({k: e.text() for k, e in self.rule_edits.items()}))
        row.addWidget(reset)
        row.addWidget(save)
        card.body.addLayout(row)
        self.rules_admin_note = Banner()
        card.body.addWidget(self.rules_admin_note)
        lay.addWidget(card)
        lay.addStretch(1)
        self._rule_buttons = (reset, save)
        return w

    def _ugc_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = Card("Printed on the UGC sheet and text file")
        form = QFormLayout()
        self.ugc_edits = {k: QLineEdit() for k in ("university_name", "university_code", "signatory_title")}
        self.ugc_edits["university_code"].setMaxLength(2)
        self.ugc_edits["university_code"].setMaximumWidth(80)
        form.addRow("University name", self.ugc_edits["university_name"])
        form.addRow("University code", self.ugc_edits["university_code"])
        form.addRow("Signatory title", self.ugc_edits["signatory_title"])
        self.line_ending = QComboBox()
        self.line_ending.addItem("Windows (CRLF)", "CRLF")
        self.line_ending.addItem("Unix (LF)", "LF")
        form.addRow("Text file line ending", self.line_ending)
        card.body.addLayout(form)
        card.body.addWidget(muted("The university code is written right-aligned in the last 2 characters of each "
                                  "text-file line (e.g. “ F”)."))
        row = QHBoxLayout()
        row.addStretch(1)
        save = button("Save", "save", "primary")
        save.clicked.connect(lambda: self._save({**{k: e.text() for k, e in self.ugc_edits.items()},
                                                 "text_line_ending": self.line_ending.currentData()}))
        row.addWidget(save)
        card.body.addLayout(row)
        self._ugc_save = save
        lay.addWidget(card)
        lay.addStretch(1)
        return w

    def _users_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addStretch(1)
        self.user_buttons = []
        for text, icon_name, fn, variant in (("Change my password", "shield", self._my_password, None),
                                             ("Reset password", "shield", self._reset_password, None),
                                             ("Activate / deactivate", "lock", self._toggle_user, None),
                                             ("Add user", "plus", self._add_user, "primary")):
            b = button(text, icon_name, variant)
            b.clicked.connect(fn)
            bar.addWidget(b)
            self.user_buttons.append(b)
        lay.addLayout(bar)
        self.users = DataTable([
            Column("Username", "username", width=150), Column("Full name", "full_name", stretch=True),
            Column("Role", "role", width=120), Column("Status", "status", width=100),
            Column("Last sign-in", "last", width=160),
        ])
        lay.addWidget(self.users, 1)
        return w

    def _backup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        card = Card("Database")
        card.body.addWidget(muted(f"Database file: {config.database_path()}\nBackups folder: {config.backup_dir()}\n"
                                  "An automatic backup is made the first time the app starts each day; the last 30 are kept."))
        row = QHBoxLayout()
        b1 = button("Back up now", "database", "primary")
        b1.clicked.connect(self._backup_now)
        b2 = button("Open backups folder", "file")
        b2.clicked.connect(self._open_backups)
        self.restore_btn = button("Restore from backup…", "upload", "danger")
        self.restore_btn.clicked.connect(self._restore)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        row.addWidget(self.restore_btn)
        card.body.addLayout(row)
        lay.addWidget(card)
        self.backups = DataTable([Column("Backup file", "name", stretch=True), Column("Size (KB)", "size", "int", width=110)])
        lay.addWidget(self.backups, 1)
        return w

    def _audit_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        search = QLineEdit()
        search.setPlaceholderText("Filter the audit log")
        lay.addWidget(search)
        self.audit = DataTable([
            Column("When", "when", width=150), Column("User", "user", width=100), Column("Action", "action", width=170),
            Column("Details", "summary", stretch=True),
        ])
        search.textChanged.connect(self.audit.set_filter)
        lay.addWidget(self.audit, 1)
        return w

    # ----- data
    def refresh(self) -> None:
        admin = self.ctx.is_admin
        with self.ctx.db.session() as s:
            values = settings.get_all(s)
            users = [{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role.title(),
                      "status": "Active" if u.is_active else "Inactive",
                      "last": u.last_login_at.strftime("%d %b %Y %H:%M") if u.last_login_at else ""}
                     for u in auth.list_users(s)]
            logs = [{"when": a.created_at.strftime("%d %b %Y %H:%M:%S") if a.created_at else "", "user": a.username,
                     "action": a.action, "summary": a.summary} for a in audit.recent(s, 2000)]
        for key, edit in self.rule_edits.items():
            edit.setText(values[key])
            edit.setReadOnly(not admin)
        for key, edit in self.ugc_edits.items():
            edit.setText(values[key])
            edit.setReadOnly(not admin)
        self.line_ending.setCurrentIndex(0 if values["text_line_ending"] == "CRLF" else 1)
        self.line_ending.setEnabled(admin)
        for b in (*self._rule_buttons, self._ugc_save, self.restore_btn, *self.user_buttons[1:]):
            b.setEnabled(admin)
        self.rules_admin_note.show_message("warning", "" if admin else "Only an administrator can change settings.")
        self.users.set_rows(users if admin else [u for u in users if u["id"] == self.ctx.user.id])
        self.audit.set_rows(logs)
        self.backups.set_rows([{"name": p.name, "size": p.stat().st_size // 1024, "path": p}
                               for p in backup.list_backups(config.backup_dir())])

    def _save(self, changes: dict[str, str]) -> None:
        try:
            with self.ctx.db.session() as s:
                settings.save(s, self.ctx.user.username, changes)
        except ServiceError as exc:
            error(self, str(exc), "Settings not saved")
            return
        self.ctx.events.data_changed.emit("settings")
        info(self, "Settings saved.")

    def _reset_rules(self) -> None:
        for key, edit in self.rule_edits.items():
            edit.setText(settings.DEFAULTS[key])

    def _add_user(self) -> None:
        dlg = UserDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            with self.ctx.db.session() as s:
                auth.create_user(s, self.ctx.user, dlg.username.text(), dlg.password.text(), dlg.full_name.text(),
                                 dlg.role.currentData())
        except ServiceError as exc:
            error(self, str(exc))
        self.refresh()

    def _ask_password(self, title: str) -> str | None:
        from PySide6.QtWidgets import QInputDialog
        pw, ok = QInputDialog.getText(self, title, f"New password (at least {auth.MIN_PASSWORD} characters):",
                                      QLineEdit.EchoMode.Password)
        return pw if ok else None

    def _my_password(self) -> None:
        pw = self._ask_password("Change my password")
        if pw is None:
            return
        try:
            with self.ctx.db.session() as s:
                auth.change_password(s, self.ctx.user, self.ctx.user.id, pw)
        except ServiceError as exc:
            error(self, str(exc))
            return
        info(self, "Password changed.")

    def _reset_password(self) -> None:
        row = self.users.selected()
        if not row:
            return
        pw = self._ask_password(f"Reset password for {row['username']}")
        if pw is None:
            return
        try:
            with self.ctx.db.session() as s:
                auth.change_password(s, self.ctx.user, row["id"], pw)
        except ServiceError as exc:
            error(self, str(exc))
            return
        info(self, "Password reset.")

    def _toggle_user(self) -> None:
        row = self.users.selected()
        if not row:
            return
        try:
            with self.ctx.db.session() as s:
                auth.set_active(s, self.ctx.user, row["id"], row["status"] != "Active")
        except ServiceError as exc:
            error(self, str(exc))
        self.refresh()

    def _backup_now(self) -> None:
        try:
            path = backup.create_backup(config.database_path(), config.backup_dir())
            with self.ctx.db.session() as s:
                audit.record(s, self.ctx.user.username, "backup.create", summary=path.name)
        except (OSError, ServiceError) as exc:
            error(self, str(exc))
            return
        self.refresh()
        info(self, f"Backup saved as {path.name}.")

    def _open_backups(self) -> None:
        folder = str(config.backup_dir())
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open" if sys.platform != "darwin" else "open", folder])

    def _restore(self) -> None:
        row = self.backups.selected()
        start = str(row["path"]) if row else str(config.backup_dir())
        path, _ = QFileDialog.getOpenFileName(self, "Choose backup", start, "Backup (*.sqlite3)")
        if not path:
            return
        try:
            backup.validate_backup(Path(path))
        except ServiceError as exc:
            error(self, str(exc))
            return
        if not confirm(self, "Restore backup", f"Replace ALL current data with {Path(path).name}?\n\n"
                       "A safety copy of the current data is saved first. The app will close; start it again "
                       "afterwards.", "Restore and close", danger=True):
            return
        try:
            self.ctx.db.dispose()
            backup.restore(Path(path), config.database_path(), config.backup_dir())
        except (OSError, ServiceError) as exc:
            error(self, f"Restore failed: {exc}")
            return
        info(self, "Backup restored. The app will now close.")
        QApplication.quit()
