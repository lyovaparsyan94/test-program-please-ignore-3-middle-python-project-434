import os

import sentry_sdk

_enabled = False


def _scrub(event: dict, hint: dict) -> dict:
    # Чистим чувствительное: cookie с идентификатором сессии, заголовки
    # (Cookie/Authorization) и тело запроса (там пароль при регистрации/входе).
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("cookies", "headers", "data"):
            request.pop(key, None)
    return event


def init_monitoring() -> None:
    global _enabled
    dsn = os.environ.get("MONITORING_DSN", "")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        # Собираем ошибки, а не производительность: трейсинг проекту не нужен.
        traces_sample_rate=0.0,
        send_default_pii=False,
        before_send=_scrub,
    )
    _enabled = True


def capture_exception(error: Exception) -> None:
    if _enabled:
        sentry_sdk.capture_exception(error)
