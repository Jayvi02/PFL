import pytest

from upf_loans.db.session import Database
from upf_loans.services import auth


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.sqlite3")
    yield database
    database.dispose()


@pytest.fixture
def admin(db):
    with db.session() as s:
        user = auth.create_user(s, None, "admin", "password123", "Admin")
    return user
