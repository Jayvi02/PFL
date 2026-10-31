"""Settings → Updates: check GitHub for a newer build and install it."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFormLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ... import config
from ...services import audit, backup, updater
from ...services.errors import ServiceError
from .. import background
from ..widgets.common import Banner, Card, button, confirm, error, muted


def short(sha: str) -> str:
    return "development copy" if sha == "dev" else sha[:7]


class UpdatesPanel(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.info: updater.UpdateInfo | None = None
        lay = QVBoxLayout(self)

        card = Card("App updates")
        card.body.addWidget(muted(
            "New versions are built on GitHub. Checking needs an internet connection; everything else in the app "
            "works offline. Your data is kept separately and is not changed by an update. A backup is made first."
        ))
        form = QFormLayout()
        self.version = QLabel(short(updater.current_build()))
        form.addRow("This version", self.version)
        card.body.addLayout(form)

        self.banner = Banner()
        card.body.addWidget(self.banner)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.hide()
        card.body.addWidget(self.progress)

        row = QHBoxLayout()
        row.addStretch(1)
        self.check_btn = button("Check for updates", "renew")
        self.check_btn.clicked.connect(self.check)
        self.install_btn = button("Download and install", "download", "primary")
        self.install_btn.clicked.connect(self._install)
        self.install_btn.hide()
        row.addWidget(self.check_btn)
        row.addWidget(self.install_btn)
        card.body.addLayout(row)
        lay.addWidget(card)
        lay.addStretch(1)

    def refresh(self) -> None:
        failure = updater.last_failure()
        if failure:
            self.banner.show_message("error", failure)

    # ----- check
    def check(self) -> None:
        self.check_btn.setEnabled(False)
        self.install_btn.hide()
        self.banner.show_message("warning", "Checking GitHub…")
        background.run(updater.check, self._checked, self._failed)

    def _checked(self, info: updater.UpdateInfo) -> None:
        self.check_btn.setEnabled(True)
        self.info = info
        if not info.available:
            self.banner.show_message("ok", "You have the latest version.")
            return
        when = info.published_at[:10]
        if not updater.is_installed_build():
            self.banner.show_message("warning", f"A new version ({short(info.latest)}, {when}) is on GitHub. "
                                     "This copy runs from source, so it can't update itself.")
            return
        self.banner.show_message("ok", f"A new version is available ({short(info.latest)}, published {when}, "
                                 f"{info.size // 1_000_000} MB).")
        self.install_btn.show()

    def _failed(self, message: str) -> None:
        self.check_btn.setEnabled(True)
        self.install_btn.setEnabled(True)
        self.progress.hide()
        self.banner.show_message("error", message)

    # ----- install
    def _install(self) -> None:
        if self.info is None:
            return
        target = updater.install_dir()
        if not updater.can_write(target):
            error(self, f"The app can't write to {target}.\n\nMove the UPFLoanManager folder somewhere you own, "
                  "such as C:\\UPFLoanManager or your Documents folder, and try again.")
            return
        if not confirm(self, "Install update", "The app will download the update, close, install it and open "
                       "again. Your data is not affected. Continue?", "Update now"):
            return
        try:
            backup.create_backup(config.database_path(), config.backup_dir(), "before-update")
        except OSError as exc:
            error(self, f"Could not make a backup before updating: {exc}")
            return
        self.install_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.banner.show_message("warning", "Downloading the update…")
        info = self.info

        def work(progress):
            zip_path = updater.download(info, progress=progress)
            new_dir = updater.unpack(zip_path)
            return updater.write_install_script(new_dir, target, updater.pid())

        background.run(work, self._downloaded, self._failed, self._progress)

    def _progress(self, done: int, total: int) -> None:
        if total:
            self.progress.setMaximum(total)
            self.progress.setValue(done)
            self.progress.setFormat(f"{done // 1_000_000} of {total // 1_000_000} MB")

    def _downloaded(self, script) -> None:
        with self.ctx.db.session() as s:
            audit.record(s, self.ctx.operator, "update.install", summary=short(self.info.latest))
        self.banner.show_message("ok", "Installing. The app will close and open again in a few seconds.")
        try:
            updater.launch_install(script)
        except OSError as exc:
            self._failed(f"Could not start the installer: {exc}")
            return
        self.ctx.db.dispose()
        QApplication.quit()
