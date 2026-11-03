from app.db import get_connection

# (slug, name)
CATEGORIES = [
    ("videokarty", "Видеокарты"),
    ("processory", "Процессоры"),
    ("materinskie-platy", "Материнские платы"),
]

# (slug, name, description, price, category_slug, image_file | None, available)
PRODUCTS = [
    ("nvidia-geforce-rtx-4070", "NVIDIA GeForce RTX 4070",
     "Видеокарта для игр в разрешении 1440p", 54990,
     "videokarty", "nvidia-geforce-rtx-4070.svg", True),
    ("nvidia-geforce-rtx-4060-ti", "NVIDIA GeForce RTX 4060 Ti",
     "Доступная видеокарта для Full HD и 1440p", 44990,
     "videokarty", "nvidia-geforce-rtx-4060-ti.svg", True),
    ("amd-radeon-rx-7800-xt", "AMD Radeon RX 7800 XT",
     "Видеокарта с 16 ГБ памяти для 1440p", 59990,
     "videokarty", "amd-radeon-rx-7800-xt.svg", True),
    ("nvidia-geforce-rtx-4090", "NVIDIA GeForce RTX 4090",
     "Флагман для 4K и тяжёлых задач", 189990,
     "videokarty", "nvidia-geforce-rtx-4090.svg", False),
    ("amd-ryzen-5-7600x", "AMD Ryzen 5 7600X",
     "Шестиядерный процессор для игр", 24990,
     "processory", "amd-ryzen-5-7600x.svg", True),
    ("intel-core-i7-14700k", "Intel Core i7-14700K",
     "Производительный процессор для игр и работы", 41990,
     "processory", "intel-core-i7-14700k.svg", True),
    ("amd-ryzen-7-7800x3d", "AMD Ryzen 7 7800X3D",
     "Игровой процессор с 3D V-Cache", 42990,
     "processory", "amd-ryzen-7-7800x3d.svg", True),
    ("amd-ryzen-9-7950x", "AMD Ryzen 9 7950X",
     "Шестнадцать ядер для сборки и рендеринга", 69990,
     "processory", "amd-ryzen-9-7950x.svg", True),
    ("asus-prime-b650m-a", "ASUS Prime B650M-A",
     "Материнская плата microATX на сокете AM5", 12990,
     "materinskie-platy", "asus-prime-b650m-a.svg", True),
    ("asrock-b650-pro-rs", "ASRock B650 Pro RS",
     "Материнская плата ATX на сокете AM5", 14990,
     "materinskie-platy", None, True),
    ("msi-mag-b760-tomahawk", "MSI MAG B760 Tomahawk",
     "Материнская плата ATX на сокете LGA1700", 18990,
     "materinskie-platy", "msi-mag-b760-tomahawk.svg", True),
    ("gigabyte-x670-aorus-elite", "Gigabyte X670 Aorus Elite",
     "Материнская плата ATX верхнего уровня на AM5", 31990,
     "materinskie-platy", "gigabyte-x670-aorus-elite.svg", True),
]

# (product_slug, title, text)
PROMOS = [
    ("nvidia-geforce-rtx-4070", "Новое поколение видеокарт",
     "GeForce RTX 4070 уже в продаже"),
    ("amd-ryzen-7-7800x3d", "Лучший процессор для игр",
     "Ryzen 7 7800X3D с технологией 3D V-Cache"),
]


def seed() -> None:
    with get_connection() as conn:
        category_ids = {}
        for position, (slug, name) in enumerate(CATEGORIES):
            row = conn.execute(
                """
                INSERT INTO categories (slug, name, position)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name, position = EXCLUDED.position
                RETURNING id
                """,
                (slug, name, position),
            ).fetchone()
            category_ids[slug] = row["id"]

        product_ids = {}
        for position, product in enumerate(PRODUCTS):
            slug, name, description, price, cat_slug, image, available = product
            image_url = f"/images/{image}" if image else None
            row = conn.execute(
                """
                INSERT INTO products (
                    slug, name, description, price_amount, currency,
                    category_id, image_url, available, position
                )
                VALUES (%s, %s, %s, %s, 'RUB', %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    price_amount = EXCLUDED.price_amount,
                    category_id = EXCLUDED.category_id,
                    image_url = EXCLUDED.image_url,
                    available = EXCLUDED.available,
                    position = EXCLUDED.position
                RETURNING id
                """,
                (slug, name, description, price,
                 category_ids[cat_slug], image_url, available, position),
            ).fetchone()
            product_ids[slug] = row["id"]

        for position, (product_slug, title, text) in enumerate(PROMOS):
            conn.execute(
                """
                INSERT INTO promos (title, text, product_id, position)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    text = EXCLUDED.text,
                    position = EXCLUDED.position
                """,
                (title, text, product_ids[product_slug], position),
            )


if __name__ == "__main__":
    seed()
