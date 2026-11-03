from pathlib import Path

from alembic import command
from alembic.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BASE_DIR / "alembic.ini"
MIGRATIONS_DIR = BASE_DIR / "migrations"


def apply_migrations() -> None:
    cfg = Config(str(ALEMBIC_INI))
    # Абсолютный путь: команда вызывается и из контейнера, и из тестов.
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    apply_migrations()
