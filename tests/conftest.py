import pytest

from upf_loans.db.session import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.sqlite3")
    yield database
    database.dispose()


@pytest.fixture
def admin():
    """Name recorded in the audit log for test actions."""
    return "officer"
