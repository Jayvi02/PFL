"""Engine/session creation and schema migration."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import resource_dir


def _sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(db_path: Path | str) -> Engine:
    url = "sqlite://" if str(db_path) == ":memory:" else f"sqlite:///{Path(db_path).as_posix()}"
    engine = create_engine(url, future=True)
    event.listen(engine, "connect", _sqlite_pragmas)
    return engine


def alembic_config(engine: Engine) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(resource_dir() / "db" / "migrations"))
    cfg.attributes["engine"] = engine
    return cfg


def migrate(engine: Engine) -> None:
    """Bring the database schema up to the latest migration."""
    command.upgrade(alembic_config(engine), "head")


class Database:
    def __init__(self, db_path: Path | str):
        self.path = db_path
        self.engine = make_engine(db_path)
        migrate(self.engine)
        self._factory = sessionmaker(self.engine, expire_on_commit=False, future=True)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
