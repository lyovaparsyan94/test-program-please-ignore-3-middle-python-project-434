"""initial schema

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE categories (
            id       bigserial PRIMARY KEY,
            slug     text NOT NULL UNIQUE,
            name     text NOT NULL,
            position int  NOT NULL DEFAULT 0
        )
    """)

    op.execute("""
        CREATE TABLE products (
            id           bigserial PRIMARY KEY,
            slug         text    NOT NULL UNIQUE,
            name         text    NOT NULL,
            description  text    NOT NULL,
            price_amount int     NOT NULL,
            currency     text    NOT NULL DEFAULT 'RUB',
            category_id  bigint  NOT NULL REFERENCES categories(id),
            image_url    text,
            available    boolean NOT NULL DEFAULT true,
            position     int     NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX products_category_id_idx ON products(category_id)")

    op.execute("""
        CREATE TABLE promos (
            id         bigserial PRIMARY KEY,
            title      text   NOT NULL,
            text       text   NOT NULL,
            product_id bigint NOT NULL UNIQUE REFERENCES products(id),
            position   int    NOT NULL DEFAULT 0
        )
    """)

    op.execute("""
        CREATE TABLE users (
            id            bigserial   PRIMARY KEY,
            email         text        NOT NULL UNIQUE,
            password_hash text        NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT now()
        )
    """)

    # Сессии в базе, а не в памяти процесса: переживают рестарт на Render.
    op.execute("""
        CREATE TABLE sessions (
            id         text        PRIMARY KEY,
            user_id    bigint      NOT NULL
                REFERENCES users(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX sessions_user_id_idx ON sessions(user_id)")

    op.execute("""
        CREATE TABLE orders (
            id             bigserial   PRIMARY KEY,
            user_id        bigint      NOT NULL REFERENCES users(id),
            status         text        NOT NULL DEFAULT 'paid',
            total_amount   int         NOT NULL,
            currency       text        NOT NULL DEFAULT 'RUB',
            method         text        NOT NULL,
            recipient_name text        NOT NULL,
            phone          text        NOT NULL,
            address        text,
            created_at     timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX orders_user_id_idx ON orders(user_id)")

    # product_id без внешнего ключа: позиция хранит снимок и не ломается,
    # если товар подорожал или исчез из каталога.
    op.execute("""
        CREATE TABLE order_items (
            id           bigserial PRIMARY KEY,
            order_id     bigint    NOT NULL
                REFERENCES orders(id) ON DELETE CASCADE,
            product_id   bigint    NOT NULL,
            product_name text      NOT NULL,
            price_amount int       NOT NULL,
            currency     text      NOT NULL DEFAULT 'RUB',
            quantity     int       NOT NULL
        )
    """)
    op.execute("CREATE INDEX order_items_order_id_idx ON order_items(order_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS order_items")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS promos")
    op.execute("DROP TABLE IF EXISTS products")
    op.execute("DROP TABLE IF EXISTS categories")
