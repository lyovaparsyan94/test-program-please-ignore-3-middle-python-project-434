import os
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
import psycopg
import pytest
import uvicorn

_DEFAULT_DB = "postgres://postgres:password@localhost:5432/appdb"


def _ensure_test_database() -> None:
    # Отдельная база для тестов: прогон не пачкает базу разработки и не
    # зависит от данных прошлых прогонов. Создаём её из служебной postgres.
    base = os.environ.get("DATABASE_URL", _DEFAULT_DB)
    parts = urlsplit(base)
    db = parts.path.lstrip("/") or "appdb"
    test_db = db if db.endswith("_test") else f"{db}_test"
    admin = urlunsplit(parts._replace(path="/postgres"))
    with psycopg.connect(admin, autocommit=True) as conn:
        found = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (test_db,)
        ).fetchone()
        if found is None:
            conn.execute(f'CREATE DATABASE "{test_db}"')
    os.environ["DATABASE_URL"] = urlunsplit(parts._replace(path=f"/{test_db}"))


_ensure_test_database()

from app.db import get_connection  # noqa: E402
from app.main import create_app  # noqa: E402
from app.migrate import apply_migrations  # noqa: E402
from app.seed import seed  # noqa: E402


def _reset_user_data() -> None:
    with get_connection() as conn:
        conn.execute(
            "TRUNCATE users, sessions, orders, order_items "
            "RESTART IDENTITY CASCADE"
        )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _self_signed_cert(directory: str) -> tuple[str, str]:
    # Сервер поднимаем по https, как проверка Хекслета: тогда cookie с флагом
    # Secure доезжает обратно и в тестах, без возни с cookie-политикой.
    cert = os.path.join(directory, "cert.pem")
    key = os.path.join(directory, "key.pem")
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", key, "-out", cert, "-days", "1",
            "-subj", "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


class _Server(uvicorn.Server):
    # Подавляем перехват сигналов: сервер живёт в треде теста.
    def install_signal_handlers(self) -> None:
        pass


@pytest.fixture(scope="session")
def base_url():
    # Известное состояние до старта сервера: схема, чистые пользовательские
    # таблицы, свежий справочный каталог.
    apply_migrations()
    _reset_user_data()
    seed()

    cert_dir = tempfile.mkdtemp()
    cert, key = _self_signed_cert(cert_dir)
    port = _free_port()
    config = uvicorn.Config(
        create_app,
        factory=True,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        ssl_certfile=cert,
        ssl_keyfile=key,
    )
    server = _Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"https://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()


@pytest.fixture
def client(base_url):
    # verify=False: сертификат самоподписанный, проверять нечего.
    with httpx.Client(base_url=base_url, verify=False) as http_client:
        yield http_client
