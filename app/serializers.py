from datetime import datetime, timezone
from typing import Any


def iso_z(dt: datetime) -> str:
    # Фронтенд парсит только суффикс Z; Python по умолчанию даёт +00:00.
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def money(amount: int, currency: str = "RUB") -> dict[str, Any]:
    # int обязателен: psycopg отдал бы numeric объектом Decimal,
    # который в JSON не сериализуется вовсе.
    return {"amount": int(amount), "currency": currency}


def category(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(row["id"]), "slug": row["slug"], "name": row["name"]}
