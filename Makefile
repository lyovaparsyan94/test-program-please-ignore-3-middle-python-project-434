PORT ?= 8080
DATABASE_URL ?= postgres://postgres:password@localhost:5432/appdb
export DATABASE_URL

install:
	uv sync

start:
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $(PORT)

lint:
	uv run ruff check

test:
	uv run pytest
