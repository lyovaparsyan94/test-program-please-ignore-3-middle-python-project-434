from contextlib import asynccontextmanager
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
from app.db import close_pool, get_db
from app.monitoring import init_monitoring
from app.orders import (
    create_order,
    get_order,
    list_orders,
    validate_order_body,
)
from app.problems import (
    on_unhandled_error,
    on_validation_error,
    problem,
)
from app.products import get_product, list_products, parse_query
from app.promos import list_promos

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


@api.get("/api/health")
def health():
    return {"status": "ok"}


@api.get("/api/categories")
def get_categories(conn=Depends(get_db)):
    return list_categories(conn)


@api.get("/api/products")
def get_products(
    category: str | None = None,
    q: str | None = None,
    priceMin: str | None = None,
    priceMax: str | None = None,
    available: str | None = None,
    page: str | None = None,
    perPage: str | None = None,
    conn=Depends(get_db),
):
    filters, error = parse_query(
        category, q, priceMin, priceMax, available, page, perPage
    )
    if error is not None:
        return problem("validation-error", error)
    return list_products(conn, filters)


@api.get("/api/products/{product_id}")
def get_product_by_id(product_id: str, conn=Depends(get_db)):
    found = get_product(conn, product_id)
    if found is None:
        return problem("not-found")
    return found


@api.get("/api/promos")
def get_promos(conn=Depends(get_db)):
    return list_promos(conn)


@api.post("/api/orders")
def create_order_route(
    request: Request, body: dict = Body(...), conn=Depends(get_db)
):
    user = _current_user(request, conn)
    if user is None:
        return problem("unauthorized")
    data, error = validate_order_body(body)
    if error is not None:
        slug, detail = error
        return problem(slug, detail)
    order, unavailable = create_order(conn, user["id"], data)
    if unavailable:
        return problem(
            "unavailable-items",
            "Some items are unavailable",
            unavailableProductIds=unavailable,
        )
    return JSONResponse(order, status_code=201)


@api.get("/api/orders")
def list_orders_route(request: Request, conn=Depends(get_db)):
    user = _current_user(request, conn)
    if user is None:
        return problem("unauthorized")
    return list_orders(conn, user["id"])


@api.get("/api/orders/{order_id}")
def get_order_route(order_id: str, request: Request, conn=Depends(get_db)):
    user = _current_user(request, conn)
    # Анониму тоже 404, не 401: существование чужого заказа не подтверждаем.
    if user is None:
        return problem("not-found")
    order = get_order(conn, user["id"], order_id)
    if order is None:
        return problem("not-found")
    return order


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
        # Одинаковый ответ на неизвестный email и неверный пароль: без этого
        # перебором собирается список зарегистрированных адресов.
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


# Аноним — 401, а не 200 с пустым телом: иначе фронтенд навсегда «загружается».
@api.get("/api/me")
def me(request: Request, conn=Depends(get_db)):
    user = _current_user(request, conn)
    if user is None:
        return problem("unauthorized")
    return public_user(user)


# Неизвестный путь под /api/ — JSON-404, не index.html. С HEAD, иначе запрос
# провалится в SPA-fallback и получит страницу.
@api.api_route(
    "/api/{path:path}",
    methods=["GET", "HEAD", "POST", "DELETE", "PUT", "PATCH"],
)
def api_not_found(path: str):
    return problem("not-found")


# Последним, после всех /api/: иначе перехватит их. HEAD нужен для curl -sI.
@fallback.api_route("/{path:path}", methods=["GET", "HEAD"])
def spa(path: str):
    file = (PUBLIC_DIR / path).resolve()
    # Без is_relative_to путь с `..` увёл бы за пределы public к файлам сервера.
    if path and file.is_relative_to(PUBLIC_DIR) and file.is_file():
        return FileResponse(file)
    return FileResponse(PUBLIC_DIR / "index.html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Закрываем пул из основного потока, иначе GC добьёт его из воркер-треда
    # с "cannot join current thread".
    close_pool()


def create_app() -> FastAPI:
    init_monitoring()
    app = FastAPI(title="Online Store API", lifespan=lifespan)
    app.add_exception_handler(RequestValidationError, on_validation_error)
    app.add_exception_handler(Exception, on_unhandled_error)
    app.include_router(api)
    app.include_router(fallback)
    return app
