PORT ?= 8080
DATABASE_URL ?= postgres://postgres:password@localhost:5432/appdb
export DATABASE_URL

FRONTEND_DIST = node_modules/@hexlet/python-online-store-frontend/dist

install:
	uv sync
	npm ci

build:
	rm -rf public/assets public/images public/index.html
	mkdir -p public
	cp -R $(FRONTEND_DIST)/. public/

start:
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $(PORT)

lint:
	uv run ruff check

test:
	uv run pytest

contract:
	npx tsp compile contract

.PHONY: install build start lint test contract
