from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse

from app.categories import list_categories
from app.db import get_db
from app.problems import (
    on_unhandled_error,
    on_validation_error,
    problem,
)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

api = APIRouter()
fallback = APIRouter()


# Healthcheck проверки и хостинга: не зависит ни от базы, ни от статики.
@api.get("/api/health")
def health():
    return {"status": "ok"}


@api.get("/api/categories")
def get_categories(conn=Depends(get_db)):
    return list_categories(conn)


# --- Временные заглушки каталога (уедут на шагах про каталог и главную) ---

@api.get("/api/products")
def list_products():
    items = [
        {
            "id": "1",
            "slug": "nvidia-geforce-rtx-4070",
            "name": "NVIDIA GeForce RTX 4070",
            "description": "Видеокарта для игр в 1440p",
            "price": {"amount": 54990, "currency": "RUB"},
            "categoryId": "1",
            "imageUrl": "/images/nvidia-geforce-rtx-4070.svg",
            "available": True,
        },
        {
            "id": "2",
            "slug": "amd-ryzen-7-7800x3d",
            "name": "AMD Ryzen 7 7800X3D",
            "description": "Игровой процессор с 3D V-Cache",
            "price": {"amount": 42990, "currency": "RUB"},
            "categoryId": "2",
            "imageUrl": "/images/amd-ryzen-7-7800x3d.svg",
            "available": True,
        },
    ]
    return {
        "items": items,
        "meta": {
            "page": 1,
            "perPage": 6,
            "total": len(items),
            "totalPages": 1,
        },
    }


@api.get("/api/promos")
def list_promos():
    return [
        {
            "id": "1",
            "title": "Новое поколение видеокарт",
            "text": "RTX 4070 уже в продаже",
            "product": {
                "id": "1",
                "slug": "nvidia-geforce-rtx-4070",
                "name": "NVIDIA GeForce RTX 4070",
                "description": "Видеокарта для игр в 1440p",
                "price": {"amount": 54990, "currency": "RUB"},
                "categoryId": "1",
                "imageUrl": "/images/nvidia-geforce-rtx-4070.svg",
                "available": True,
            },
        },
    ]


# Пока авторизации нет, аноним получает 401, а не 200 с пустым телом:
# иначе фронтенд навсегда остаётся в состоянии загрузки.
@api.get("/api/me")
def me():
    return problem("unauthorized")


# Любой путь под /api/ — JSON-404, а не index.html. HEAD обязателен: без него
# HEAD /api/... провалился бы в SPA-fallback и отдал бы страницу.
@api.api_route(
    "/api/{path:path}",
    methods=["GET", "HEAD", "POST", "DELETE", "PUT", "PATCH"],
)
def api_not_found(path: str):
    return problem("not-found")


# SPA-fallback — последним, после всех /api/. HEAD нужен для статики (curl -sI).
@fallback.api_route("/{path:path}", methods=["GET", "HEAD"])
def spa(path: str):
    file = (PUBLIC_DIR / path).resolve()
    # is_relative_to: `..` в пути из запроса иначе увёл бы за пределы public.
    if path and file.is_relative_to(PUBLIC_DIR) and file.is_file():
        return FileResponse(file)
    return FileResponse(PUBLIC_DIR / "index.html")


def create_app() -> FastAPI:
    app = FastAPI(title="Online Store API")
    app.add_exception_handler(RequestValidationError, on_validation_error)
    app.add_exception_handler(Exception, on_unhandled_error)
    app.include_router(api)
    app.include_router(fallback)
    return app
