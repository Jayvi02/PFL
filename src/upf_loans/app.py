"""Application entry point."""

from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from . import config
from .db.session import Database
from .services import backup, settings


def _setup_logging() -> None:
    logging.basicConfig(
        filename=config.data_dir() / "upf_loans.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _excepthook(exc_type, exc, tb) -> None:
    logging.error("Unhandled error", exc_info=(exc_type, exc, tb))
    QMessageBox.critical(None, "Unexpected error",
                         f"{exc}\n\nDetails were written to {config.data_dir() / 'upf_loans.log'}.")


def self_test() -> int:
    """`UPFLoanManager.exe --self-test`: check the bundle can create and migrate a database."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "check.sqlite3")
        with db.session() as s:
            settings.loan_rules(s)
        db.dispose()
    print("self-test ok")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    _setup_logging()
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.APP_DIR_NAME)
    app.setFont(QFont("Segoe UI", 10))
    from .ui.theme import STYLESHEET
    from .ui.icons import icon
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(icon("wallet", "#1F3A68", 32))

    try:
        db_path = config.database_path()
        try:
            backup.auto_backup_if_due(db_path, config.backup_dir())
        except Exception:  # noqa: BLE001 - a failed backup must not stop the app
            logging.exception("Automatic backup failed")
        db = Database(db_path)
        with db.session() as s:
            keep = int(settings.get(s, "backup_keep") or 30)
        backup.prune(config.backup_dir(), keep)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Could not open database")
        QMessageBox.critical(None, config.APP_NAME, f"The database could not be opened:\n{exc}\n\n{traceback.format_exc(limit=2)}")
        return 1

    from .ui.context import AppContext, Events
    from .ui.main_window import MainWindow

    window = MainWindow(AppContext(db=db, events=Events()))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
