import threading
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_database_url

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _configure(conn: psycopg.Connection) -> None:
    # Пояс сессии — UTC (сервер БД локально и на Render разный).
    # В autocommit SET фиксируется сразу и не держит соединение в транзакции.
    conn.execute("SET TIME ZONE 'UTC'")


def get_pool() -> ConnectionPool:
    # Двойная проверка под блокировкой: без неё два одновременных первых
    # запроса создают два пула, лишний осиротевает и роняет в логи
    # "cannot join current thread" при сборке мусора.
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    conninfo=get_database_url(),
                    min_size=1,
                    max_size=10,
                    # autocommit: запись фиксируется до отправки ответа, а не
                    # в teardown зависимости (после ответа). Иначе быстрый
                    # запрос вслед за DELETE /api/session увидел бы живую
                    # сессию. Многошаговые операции — в conn.transaction().
                    kwargs={"row_factory": dict_row, "autocommit": True},
                    configure=_configure,
                    open=True,
                )
    return _pool


def close_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


def get_db() -> Iterator[psycopg.Connection]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
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
