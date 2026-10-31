from alembic import context

from upf_loans.db.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = config.attributes.get("engine")
    if engine is None:
        from sqlalchemy import create_engine

        engine = create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        context.run_migrations()


run_migrations_online()
