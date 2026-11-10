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


def product(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": str(row["id"]),
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"],
        "price": money(row["price_amount"], row["currency"]),
        "categoryId": str(row["category_id"]),
        "available": row["available"],
    }
    # Пустую строку не отдаём: фронтенд нарисует заглушку только без поля.
    if row["image_url"]:
        result["imageUrl"] = row["image_url"]
    return result


def shipping(order_row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "method": order_row["method"],
        "recipientName": order_row["recipient_name"],
        "phone": order_row["phone"],
    }
    if order_row["address"]:
        result["address"] = order_row["address"]
    return result


def order(order_row: dict[str, Any], item_rows: list[dict]) -> dict[str, Any]:
    return {
        "id": str(order_row["id"]),
        "status": order_row["status"],
        "items": [
            {
                "productId": str(item["product_id"]),
                "productName": item["product_name"],
                "priceAtPurchase": money(
                    item["price_amount"], item["currency"]
                ),
                "quantity": item["quantity"],
            }
            for item in item_rows
        ],
        "shipping": shipping(order_row),
        "total": money(order_row["total_amount"], order_row["currency"]),
        "createdAt": iso_z(order_row["created_at"]),
    }
