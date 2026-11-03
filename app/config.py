import os


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def get_sqlalchemy_url() -> str:
    # Alembic работает через SQLAlchemy-engine; psycopg 3 сидит на схеме
    # postgresql+psycopg. CI и Render отдают postgres:// или postgresql://.
    url = get_database_url()
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
