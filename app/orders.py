from collections import defaultdict

import psycopg

from app.serializers import order as serialize_order

# Ошибка валидации: (тип Problem Details, технический текст) либо None.
Error = tuple[str, str]


def _valid_quantity(value: object) -> bool:
    # bool — подкласс int, но количество булевым быть не должно.
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 1
    )


def _validate_items(items: object) -> tuple[list | None, Error | None]:
    if not isinstance(items, list) or len(items) == 0:
        return None, ("validation-error", "items must be a non-empty array")
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            return None, ("validation-error", "each item must be an object")
        product_id = item.get("productId")
        quantity = item.get("quantity")
        if not isinstance(product_id, str) or not product_id:
            return None, ("validation-error", "productId is required")
        if not _valid_quantity(quantity):
            return None, ("validation-error", "quantity must be >= 1")
        parsed.append((product_id, quantity))
    return parsed, None


def _validate_shipping(shipping: object) -> tuple[dict | None, Error | None]:
    if not isinstance(shipping, dict):
        return None, ("validation-error", "shipping is required")
    method = shipping.get("method")
    recipient = shipping.get("recipientName")
    phone = shipping.get("phone")
    address = shipping.get("address")
    if method not in ("delivery", "pickup"):
        return None, ("validation-error", "method must be delivery or pickup")
    if not isinstance(recipient, str) or not recipient.strip():
        return None, ("validation-error", "recipientName is required")
    if not isinstance(phone, str) or not phone.strip():
        return None, ("validation-error", "phone is required")
    if address is not None and not isinstance(address, str):
        return None, ("validation-error", "address must be a string")
    # Адрес проверяем на непустоту после trim: строка из пробелов — не адрес.
    if method == "delivery" and (not address or not address.strip()):
        return None, ("address-required", "address is required for delivery")
    return {
        "method": method,
        "recipientName": recipient,
        "phone": phone,
        "address": address if method == "delivery" else None,
    }, None


def _merge_items(parsed: list) -> list:
    # Один и тот же товар в items суммируем в одну позицию.
    merged: dict[str, int] = defaultdict(int)
    order: list[str] = []
    for product_id, quantity in parsed:
        if product_id not in merged:
            order.append(product_id)
        merged[product_id] += quantity
    return [(product_id, merged[product_id]) for product_id in order]


def validate_order_body(body: object) -> tuple[dict | None, Error | None]:
    if not isinstance(body, dict):
        return None, ("validation-error", "Invalid order body")
    parsed_items, error = _validate_items(body.get("items"))
    if error is not None:
        return None, error
    shipping, error = _validate_shipping(body.get("shipping"))
    if error is not None:
        return None, error
    return {"items": _merge_items(parsed_items), "shipping": shipping}, None


def create_order(
    conn: psycopg.Connection, user_id: int, data: dict
) -> tuple[dict | None, list[str]]:
    requested = data["items"]
    numeric_ids = [int(pid) for pid, _ in requested if pid.isdigit()]

    products = {}
    if numeric_ids:
        rows = conn.execute(
            """
            SELECT id, name, price_amount, currency, available
            FROM products WHERE id = ANY(%s)
            """,
            (numeric_ids,),
        ).fetchall()
        products = {row["id"]: row for row in rows}

    # Собираем ВСЕ проблемные id, а не падаем на первом. Нечисловой id —
    # это ненайденный товар.
    unavailable = []
    resolved = []
    for product_id, quantity in requested:
        row = products.get(int(product_id)) if product_id.isdigit() else None
        if row is None or not row["available"]:
            unavailable.append(product_id)
        else:
            resolved.append((product_id, row, quantity))
    if unavailable:
        return None, unavailable

    total = sum(row["price_amount"] * qty for _, row, qty in resolved)
    shipping = data["shipping"]

    # Заказ и позиции — в одной транзакции: заказ без позиций хуже отсутствия.
    with conn.transaction():
        order_row = conn.execute(
            """
            INSERT INTO orders (
                user_id, status, total_amount, currency,
                method, recipient_name, phone, address
            )
            VALUES (%s, 'paid', %s, 'RUB', %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id, total, shipping["method"],
                shipping["recipientName"], shipping["phone"],
                shipping["address"],
            ),
        ).fetchone()
        order_id = order_row["id"]
        for product_id, row, quantity in resolved:
            conn.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_name,
                    price_amount, currency, quantity
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (order_id, int(product_id), row["name"],
                 row["price_amount"], row["currency"], quantity),
            )

    return get_order(conn, user_id, str(order_id)), []


def get_order(
    conn: psycopg.Connection, user_id: int, order_id: str
) -> dict | None:
    if not order_id.isdigit():
        return None
    # Изоляция условием запроса: чужой заказ не отдать по невнимательности.
    order_row = conn.execute(
        "SELECT * FROM orders WHERE id = %s AND user_id = %s",
        (int(order_id), user_id),
    ).fetchone()
    if order_row is None:
        return None
    item_rows = conn.execute(
        """
        SELECT product_id, product_name, price_amount, currency, quantity
        FROM order_items WHERE order_id = %s ORDER BY id
        """,
        (int(order_id),),
    ).fetchall()
    return serialize_order(order_row, item_rows)


def list_orders(conn: psycopg.Connection, user_id: int) -> list[dict]:
    orders = conn.execute(
        """
        SELECT * FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        """,
        (user_id,),
    ).fetchall()
    if not orders:
        return []

    order_ids = [order["id"] for order in orders]
    item_rows = conn.execute(
        """
        SELECT order_id, product_id, product_name, price_amount,
               currency, quantity
        FROM order_items WHERE order_id = ANY(%s) ORDER BY id
        """,
        (order_ids,),
    ).fetchall()
    items_by_order = defaultdict(list)
    for item in item_rows:
        items_by_order[item["order_id"]].append(item)

    return [
        serialize_order(order, items_by_order[order["id"]])
        for order in orders
    ]
