import hashlib
import hmac
import re
import secrets

import psycopg

SESSION_COOKIE = "session"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Параметры scrypt (OWASP-профиль для интерактивного входа).
_N = 2 ** 14
_R = 8
_P = 1
_DKLEN = 32


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_credentials(body: object) -> tuple[str, str] | None:
    # Сначала нормализуем email, потом проверяем формат: " A@B.COM " проходит
    # и совпадает с a@b.com. Возвращаем None на любую проблему формы.
    if not isinstance(body, dict):
        return None
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return None
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        return None
    if len(password) < 6:
        return None
    return email, password


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


# Для неизвестного email считаем хеш против заглушки: время ответа тогда
# не выдаёт, зарегистрирован адрес или нет.
_DUMMY_HASH = hash_password("timing-equalizer")


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, hash_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(hash_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    # compare_digest: время сравнения не зависит от места расхождения.
    return hmac.compare_digest(digest.hex(), hash_hex)


def create_user(
    conn: psycopg.Connection, email: str, password: str
) -> dict | None:
    existing = conn.execute(
        "SELECT id FROM users WHERE email = %s", (email,)
    ).fetchone()
    if existing is not None:
        return None
    try:
        # Савепоинт: при гонке на уникальном индексе откат только вставки,
        # соединение остаётся рабочим, а ошибка превращается в 409, не 500.
        with conn.transaction():
            row = conn.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email
                """,
                (email, hash_password(password)),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        return None
    return row


def authenticate(
    conn: psycopg.Connection, email: str, password: str
) -> dict | None:
    row = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = %s",
        (email,),
    ).fetchone()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"]}


def create_session(conn: psycopg.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (id, user_id) VALUES (%s, %s)",
        (token, user_id),
    )
    return token


def delete_session(conn: psycopg.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE id = %s", (token,))


def user_by_session(conn: psycopg.Connection, token: str) -> dict | None:
    # Протухшую сессию не принимаем, даже если cookie ещё жива.
    return conn.execute(
        """
        SELECT users.id, users.email
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.id = %s
          AND sessions.created_at > now() - interval '30 days'
        """,
        (token,),
    ).fetchone()


def public_user(user: dict) -> dict:
    return {"id": str(user["id"]), "email": user["email"]}
