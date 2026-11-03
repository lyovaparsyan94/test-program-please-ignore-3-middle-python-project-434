from typing import Any

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.monitoring import capture_exception

# Закрытый словарь типов ошибок (RFC 9457), тот же, что в контракте.
# title и detail технические: текст пользователю подбирает фронтенд по type.
_PROBLEMS: dict[str, tuple[int, str]] = {
    "invalid-credentials": (401, "Invalid email or password"),
    "email-taken": (409, "Email already taken"),
    "address-required": (400, "Address is required for delivery"),
    "unavailable-items": (400, "Some items are unavailable"),
    "validation-error": (400, "Request validation failed"),
    "unauthorized": (401, "Authentication required"),
    "not-found": (404, "Resource not found"),
    "internal-error": (500, "Internal server error"),
}


def problem(
    slug: str,
    detail: str | None = None,
    **extra: Any,
) -> JSONResponse:
    status, title = _PROBLEMS[slug]
    body: dict[str, Any] = {
        "type": f"/problems/{slug}",
        "title": title,
        "status": status,
    }
    if detail is not None:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status)


# FastAPI по умолчанию отдаёт 422 {"detail": [...]}; контракт требует 400
# с типом validation-error. Обработчик один на всё приложение.
def on_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return problem("validation-error", "Request body or parameters are invalid")


def on_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    # Сюда долетают только непредвиденные ошибки: ожидаемые ответы
    # (401/400/404) отдаются через problem() напрямую, мимо сборщика.
    capture_exception(exc)
    return problem("internal-error")
