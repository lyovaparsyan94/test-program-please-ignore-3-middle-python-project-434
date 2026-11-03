import os
import socket
import threading
import time

import httpx
import pytest
import uvicorn

# Локальный дефолт для разработки. В CI DATABASE_URL задаёт workflow,
# и setdefault его тогда не перезапишет.
os.environ.setdefault(
    "DATABASE_URL",
    "postgres://postgres:password@localhost:5432/appdb",
)

from app.main import create_app  # noqa: E402
from app.migrate import apply_migrations  # noqa: E402
from app.seed import seed  # noqa: E402


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _Server(uvicorn.Server):
    # Подавляем перехват сигналов: сервер живёт в треде теста.
    def install_signal_handlers(self) -> None:
        pass


@pytest.fixture(scope="session")
def base_url():
    # Приводим базу в известное состояние до старта сервера.
    apply_migrations()
    seed()

    port = _free_port()
    config = uvicorn.Config(
        create_app,
        factory=True,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = _Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()


@pytest.fixture
def client(base_url):
    with httpx.Client(base_url=base_url) as http_client:
        yield http_client
