from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QTabWidget, QVBoxLayout, QWidget,
)

from ... import config
from ...services import audit, backup, settings
from ...services.errors import ServiceError
from ..widgets.common import Card, button, confirm, error, info, muted
from ..widgets.table import Column, DataTable
from .base import Page
from .updates_panel import UpdatesPanel

RULE_FIELDS = [
    ("salary_multiplier", "Salary multiplier", "Cap 1: salary × this (Excel column U, default 48)"),
    ("salary_balance_multiplier", "Salary balance multiplier", "Cap 2: salary balance × this (column V, default 120)"),
    ("pf_balance_ratio", "PF balance ratio", "Cap 3: PF balance × this (column W, default 0.65)"),
    ("surety_allowance_ratio", "Q allowance ratio", "Q above PF balance × this is deducted (column Y, default 0.1)"),
    ("instalment_months", "Number of instalments", "Loan = whole instalments × this (columns Z/AA, default 120)"),
]


class SettingsPage(Page):
    title = "Settings"
    subtitle = "Loan rules, UGC details, backups and app updates"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.tabs = QTabWidget()
        self.check_updates_btn = button("Check for updates", "refresh", "primary")
        self.check_updates_btn.clicked.connect(lambda: self.open_with("updates"))
        self.tabs.setCornerWidget(self.check_updates_btn, Qt.Corner.TopRightCorner)
        self.root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._rules_tab(), "Loan rules")
        self.tabs.addTab(self._ugc_tab(), "University && UGC")
        self.tabs.addTab(self._backup_tab(), "Backup && restore")
        self.tabs.addTab(self._audit_tab(), "Audit log")
        self.updates = UpdatesPanel(ctx)
        self.tabs.addTab(self.updates, "Updates")

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
        lay.addWidget(card)
        lay.addStretch(1)
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
        lay.addWidget(card)
        lay.addStretch(1)
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
            Column("When", "when", width=150), Column("By", "user", width=100), Column("Action", "action", width=170),
            Column("Details", "summary", stretch=True),
        ])
        search.textChanged.connect(self.audit.set_filter)
        lay.addWidget(self.audit, 1)
        return w

    # ----- data
    def open_with(self, arg) -> None:
        if arg == "updates":
            self.tabs.setCurrentWidget(self.updates)
            self.updates.check()

    def refresh(self) -> None:
        self.updates.refresh()
        with self.ctx.db.session() as s:
            values = settings.get_all(s)
            logs = [{"when": a.created_at.strftime("%d %b %Y %H:%M:%S") if a.created_at else "", "user": a.username,
                     "action": a.action, "summary": a.summary} for a in audit.recent(s, 2000)]
        for key, edit in self.rule_edits.items():
            edit.setText(values[key])
        for key, edit in self.ugc_edits.items():
            edit.setText(values[key])
        self.line_ending.setCurrentIndex(0 if values["text_line_ending"] == "CRLF" else 1)
        self.audit.set_rows(logs)
        self.backups.set_rows([{"name": p.name, "size": p.stat().st_size // 1024, "path": p}
                               for p in backup.list_backups(config.backup_dir())])

    def _save(self, changes: dict[str, str]) -> None:
        try:
            with self.ctx.db.session() as s:
                settings.save(s, self.ctx.operator, changes)
        except ServiceError as exc:
            error(self, str(exc), "Settings not saved")
            return
        self.ctx.events.data_changed.emit("settings")
        info(self, "Settings saved.")

    def _reset_rules(self) -> None:
        for key, edit in self.rule_edits.items():
            edit.setText(settings.DEFAULTS[key])

    def _backup_now(self) -> None:
        try:
            path = backup.create_backup(config.database_path(), config.backup_dir())
            with self.ctx.db.session() as s:
                audit.record(s, self.ctx.operator, "backup.create", summary=path.name)
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
