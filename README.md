# Бекенд для интернет-магазина (Python)

[![hexlet-check](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-434/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-434/actions)
[![main](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-434/actions/workflows/main.yml/badge.svg)](https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-434/actions/workflows/main.yml)

Бекенд интернет-магазина комплектующих: регистрация и авторизация, каталог с
фильтрами и пагинацией, промо-блоки главной, оформление заказа и личный кабинет
с историей заказов. Данные хранятся в PostgreSQL. Фронтенд — готовое приложение
от Хекслета, которое подключается к API и работает по описанному контракту
(реализованы все двенадцать эндпоинтов под `/api`).

Учебный проект Хекслета: https://ru.hexlet.io/programs/test-program-please-ignore-3-middle-python
Как это должно работать: https://files.hexlet.app/a/qf7bsq

## Демо

Развёрнутое приложение: <!-- DEPLOY_URL -->

> На бесплатном плане Render сервис засыпает при простое — первый запрос может идти около минуты.

## Стек

- Python 3.13, FastAPI, Uvicorn
- PostgreSQL, psycopg 3, Alembic (миграции)
- uv — менеджер зависимостей; Docker — запуск и деплой

## Требования

- Python 3.13, [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16+ (или Docker)
- Node.js 22+ — только чтобы установить npm-пакет с фронтендом

## Установка

```bash
git clone https://github.com/lyovaparsyan94/test-program-please-ignore-3-middle-python-project-434.git
cd test-program-please-ignore-3-middle-python-project-434
make install   # uv sync + npm ci
make build     # раскладывает статику фронтенда в public/
```

Переменные окружения:

- `DATABASE_URL` — строка подключения к PostgreSQL (по умолчанию `postgres://postgres:password@localhost:5432/appdb`)
- `PORT` — порт сервера (по умолчанию `8080`)
- `MONITORING_DSN` — DSN сборщика ошибок (необязательна; без неё мониторинг выключен)

## Использование

```bash
make start   # применяет миграции, заливает каталог и запускает сервер
```

Приложение будет доступно на `http://localhost:8080`.

## Тесты

```bash
make lint   # ruff
make test   # тесты API на pytest
```

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
