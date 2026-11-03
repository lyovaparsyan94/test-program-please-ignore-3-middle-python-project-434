from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_database_url

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    # Пояс сессии — UTC (сервер БД локально и на Render разный).
    # commit обязателен: иначе SET держит соединение в транзакции,
    # и пул его отбросит.
    conn.execute("SET TIME ZONE 'UTC'")
    conn.commit()


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_database_url(),
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            configure=_configure,
            open=True,
        )
    return _pool


def get_db() -> Iterator[psycopg.Connection]:
    # Соединение из пула на запрос; finally гарантирует возврат.
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    # Разовое соединение для миграций и заливки, мимо пула запросов.
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        conn.execute("SET TIME ZONE 'UTC'")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
