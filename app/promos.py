import psycopg

from app.serializers import product


def list_promos(conn: psycopg.Connection) -> list[dict]:
    # Один запрос с соединением: товар уходит вложенным, без N+1.
    rows = conn.execute(
        """
        SELECT pr.id AS promo_id, pr.title, pr.text,
               p.id, p.slug, p.name, p.description, p.price_amount,
               p.currency, p.category_id, p.image_url, p.available
        FROM promos pr
        JOIN products p ON p.id = pr.product_id
        ORDER BY pr.position, pr.id
        """
    ).fetchall()
    return [
        {
            "id": str(row["promo_id"]),
            "title": row["title"],
            "text": row["text"],
            "product": product(row),
        }
        for row in rows
    ]
