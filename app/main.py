from pathlib import Path

from fastapi import APIRouter, Body, Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.auth import (
    SESSION_COOKIE,
    authenticate,
    create_session,
    create_user,
    delete_session,
    public_user,
    user_by_session,
    validate_credentials,
)
from app.categories import list_categories
from app.db import get_db
from app.problems import (
    on_unhandled_error,
    on_validation_error,
    problem,
)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
SESSION_MAX_AGE = 60 * 60 * 24 * 30

api = APIRouter()
fallback = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _current_user(request: Request, conn) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return user_by_session(conn, token)


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


@api.post("/api/users")
def register(body: dict = Body(...), conn=Depends(get_db)):
    credentials = validate_credentials(body)
    if credentials is None:
        return problem("validation-error", "Invalid email or password")
    email, password = credentials
    user = create_user(conn, email, password)
    if user is None:
        return problem("email-taken")
    token = create_session(conn, user["id"])
    response = JSONResponse(public_user(user), status_code=201)
    _set_session_cookie(response, token)
    return response


@api.post("/api/session")
def login(body: dict = Body(...), conn=Depends(get_db)):
    credentials = validate_credentials(body)
    if credentials is None:
        return problem("validation-error", "Invalid email or password")
    email, password = credentials
    user = authenticate(conn, email, password)
    if user is None:
        # Один и тот же ответ на неизвестный email и неверный пароль:
        # иначе перебором собирается список зарегистрированных адресов.
        return problem("invalid-credentials")
    token = create_session(conn, user["id"])
    response = JSONResponse(public_user(user))
    _set_session_cookie(response, token)
    return response


@api.delete("/api/session")
def logout(request: Request, conn=Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(conn, token)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# Единственный способ, которым фронтенд узнаёт состояние входа.
# Аноним получает 401, а не 200 с пустым телом: иначе фронтенд навсегда
# остаётся в состоянии загрузки.
@api.get("/api/me")
def me(request: Request, conn=Depends(get_db)):
    user = _current_user(request, conn)
    if user is None:
        return problem("unauthorized")
    return public_user(user)


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
