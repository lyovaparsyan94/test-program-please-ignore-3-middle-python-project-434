from typing import Any

import psycopg

from app.serializers import product

PER_PAGE_DEFAULT = 6
PER_PAGE_MAX = 48


def _parse_int(
    value: str | None,
    name: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{name} must be an integer"
    if minimum is not None and parsed < minimum:
        return None, f"{name} must be >= {minimum}"
    if maximum is not None and parsed > maximum:
        return None, f"{name} must be <= {maximum}"
    return parsed, None


def _parse_bool(value: str | None) -> tuple[bool | None, str | None]:
    if value is None or value == "":
        return None, None
    low = value.lower()
    if low in ("true", "1"):
        return True, None
    if low in ("false", "0"):
        return False, None
    return None, "available must be a boolean"


def parse_query(
    category: str | None,
    q: str | None,
    price_min: str | None,
    price_max: str | None,
    available: str | None,
    page: str | None,
    per_page: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    price_min_v, error = _parse_int(price_min, "priceMin")
    if error:
        return None, error
    price_max_v, error = _parse_int(price_max, "priceMax")
    if error:
        return None, error
    available_v, error = _parse_bool(available)
    if error:
        return None, error
    page_v, error = _parse_int(page, "page", minimum=1)
    if error:
        return None, error
    per_page_v, error = _parse_int(
        per_page, "perPage", minimum=1, maximum=PER_PAGE_MAX
    )
    if error:
        return None, error

    filters = {
        # Пустая строка — это "все категории", а не категория с пустым слагом.
        "category": category or None,
        "q": q or None,
        "priceMin": price_min_v,
        "priceMax": price_max_v,
        "available": available_v,
        "page": page_v or 1,
        "perPage": per_page_v or PER_PAGE_DEFAULT,
    }
    return filters, None


def _build_conditions(filters: dict) -> tuple[str, dict]:
    conditions = []
    params: dict[str, Any] = {}
    if filters["category"]:
        conditions.append("c.slug = %(category)s")
        params["category"] = filters["category"]
    if filters["q"]:
        conditions.append("p.name ILIKE %(q)s")
        params["q"] = f"%{filters['q']}%"
    if filters["priceMin"] is not None:
        conditions.append("p.price_amount >= %(priceMin)s")
        params["priceMin"] = filters["priceMin"]
    if filters["priceMax"] is not None:
        conditions.append("p.price_amount <= %(priceMax)s")
        params["priceMax"] = filters["priceMax"]
    if filters["available"] is not None:
        conditions.append("p.available = %(available)s")
        params["available"] = filters["available"]
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def list_products(conn: psycopg.Connection, filters: dict) -> dict:
    where, params = _build_conditions(filters)
    base = f"FROM products p JOIN categories c ON c.id = p.category_id{where}"

    total = conn.execute(
        f"SELECT count(*) AS total {base}", params
    ).fetchone()["total"]

    page = filters["page"]
    per_page = filters["perPage"]
    rows = conn.execute(
        f"""
        SELECT p.id, p.slug, p.name, p.description, p.price_amount,
               p.currency, p.category_id, p.image_url, p.available
        {base}
        ORDER BY p.position, p.id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**params, "limit": per_page, "offset": (page - 1) * per_page},
    ).fetchall()

    total_pages = (total + per_page - 1) // per_page
    return {
        "items": [product(row) for row in rows],
        "meta": {
            "page": page,
            "perPage": per_page,
            "total": total,
            "totalPages": total_pages,
        },
    }


def get_product(conn: psycopg.Connection, product_id: str) -> dict | None:
    # Нечисловой идентификатор — это несуществующий товар, а не 500 на запросе.
    if not product_id.isdigit():
        return None
    row = conn.execute(
        """
        SELECT id, slug, name, description, price_amount,
               currency, category_id, image_url, available
        FROM products WHERE id = %s
        """,
        (int(product_id),),
    ).fetchone()
    return product(row) if row is not None else None
