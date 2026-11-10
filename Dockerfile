# 1) Собранный фронтенд Хекслета — забираем из npm-пакета
FROM node:26-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 2) Рантайм
FROM python:3.13-slim

# uv ставит зависимости по uv.lock — тот же менеджер, что и локально
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

# make нужен: образ запускается через `make start`, той же командой, что локально
RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Логи без буферизации: иначе вывод приложения виснет в буфере, и логи на Render
# пусты ровно тогда, когда нужны — при разборе упавшего деплоя.
ENV PYTHONUNBUFFERED=1
# Кеш uv и окружение проекта на разных слоях образа, hardlink между ними невозможен.
ENV UV_LINK_MODE=copy

WORKDIR /app

# --frozen: ставим ровно то, что в uv.lock. --no-dev: pytest и линтер в проде не нужны.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
COPY --from=frontend \
    /build/node_modules/@hexlet/python-online-store-frontend/dist/. ./public/

# EXPOSE не нужен: порт приходит из PORT, фиксированное число здесь врало бы.
# Миграции, заливка и старт сервера — при запуске контейнера.
# --no-sync: окружение уже собрано выше, иначе uv run на старте дотянул бы
#   dev-группу (pytest/ruff), что медлит холодный старт и требует реестра.
# exec: uvicorn становится процессом 1 и получает SIGTERM от Render, поэтому
#   отрабатывает закрытие пула в lifespan.
CMD ["sh", "-c", "uv run --no-sync python -m app.migrate && uv run --no-sync python -m app.seed && exec uv run --no-sync uvicorn --factory app.main:create_app --host 0.0.0.0 --port ${PORT:-8080}"]
