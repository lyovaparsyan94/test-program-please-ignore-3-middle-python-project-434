import psycopg

from app.serializers import category


def list_categories(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, slug, name FROM categories ORDER BY position, id"
    ).fetchall()
    return [category(row) for row in rows]
