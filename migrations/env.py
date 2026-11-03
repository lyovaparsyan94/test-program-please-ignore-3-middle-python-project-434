from alembic import context
from sqlalchemy import create_engine

from app.config import get_sqlalchemy_url


def run_migrations_online() -> None:
    engine = create_engine(get_sqlalchemy_url())
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
