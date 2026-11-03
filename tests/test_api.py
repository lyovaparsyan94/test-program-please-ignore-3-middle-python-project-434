import uuid

import pytest

from app.main import PUBLIC_DIR


def _unique_email():
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _register(client, password="secret1"):
    email = _unique_email()
    response = client.post(
        "/api/users", json={"email": email, "password": password}
    )
    assert response.status_code == 201
    return email


def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_path_returns_json_404(client):
    response = client.get("/api/nothing-here")
    assert response.status_code == 404
    body = response.json()
    assert body["type"] == "/problems/not-found"
    assert body["status"] == 404


@pytest.mark.skipif(
    not (PUBLIC_DIR / "index.html").exists(),
    reason="frontend is not built (run make build)",
)
def test_spa_fallback_serves_index_on_direct_cart(client):
    response = client.get("/cart")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_categories_from_db(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert {"videokarty", "processory"} <= {c["slug"] for c in data}
    for item in data:
        assert set(item) >= {"id", "slug", "name"}
        assert isinstance(item["id"], str)


def test_register_opens_session(client):
    email = _register(client)
    me = client.get("/api/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == email
    assert isinstance(body["id"], str)
    assert "password" not in body
    assert "passwordHash" not in body


def test_register_duplicate_email_is_conflict(client):
    email = _register(client)
    # Тот же адрес в другом регистре — тот же пользователь.
    response = client.post(
        "/api/users", json={"email": email.upper(), "password": "secret1"}
    )
    assert response.status_code == 409
    assert response.json()["type"] == "/problems/email-taken"


def test_register_invalid_body_is_validation_error(client):
    bad_email = client.post(
        "/api/users", json={"email": "not-an-email", "password": "secret1"}
    )
    assert bad_email.status_code == 400
    assert bad_email.json()["type"] == "/problems/validation-error"

    short_pw = client.post(
        "/api/users", json={"email": _unique_email(), "password": "123"}
    )
    assert short_pw.status_code == 400
    assert short_pw.json()["type"] == "/problems/validation-error"


def test_login_success(client):
    email = _register(client)
    client.delete("/api/session")
    response = client.post(
        "/api/session", json={"email": email, "password": "secret1"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_login_wrong_password_is_401(client):
    email = _register(client)
    client.delete("/api/session")
    response = client.post(
        "/api/session", json={"email": email, "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert response.json()["type"] == "/problems/invalid-credentials"


def test_login_unknown_email_is_401(client):
    response = client.post(
        "/api/session",
        json={"email": _unique_email(), "password": "secret1"},
    )
    assert response.status_code == 401
    assert response.json()["type"] == "/problems/invalid-credentials"


def test_me_anonymous_is_401(client):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["type"] == "/problems/unauthorized"


def test_logout_ends_session_server_side(client):
    _register(client)
    saved = client.cookies.get("session")
    assert saved
    assert client.delete("/api/session").status_code == 204
    # Даже со старой cookie сессия на сервере уже завершена.
    response = client.get(
        "/api/me", headers={"Cookie": f"session={saved}"}
    )
    assert response.status_code == 401
