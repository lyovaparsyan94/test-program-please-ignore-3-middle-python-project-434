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


def test_products_no_filters_paginates(client):
    page1 = client.get("/api/products").json()
    assert page1["meta"]["page"] == 1
    assert page1["meta"]["perPage"] == 6
    assert page1["meta"]["total"] >= 12
    assert len(page1["items"]) == 6
    assert page1["meta"]["totalPages"] == (page1["meta"]["total"] + 5) // 6
    # id — строка, цена — целое число.
    item = page1["items"][0]
    assert isinstance(item["id"], str)
    assert isinstance(item["price"]["amount"], int)


def test_products_second_page_differs(client):
    page1 = client.get("/api/products?page=1").json()
    page2 = client.get("/api/products?page=2").json()
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_products_filter_by_category(client):
    data = client.get("/api/products?category=videokarty&perPage=48").json()
    assert data["meta"]["total"] == 4
    # Все товары выдачи из одной категории.
    assert len({i["categoryId"] for i in data["items"]}) == 1


def test_products_search_is_case_insensitive(client):
    data = client.get("/api/products?q=rtx&perPage=48").json()
    assert data["meta"]["total"] == 3
    assert all("RTX" in i["name"] for i in data["items"])


def test_products_price_filter_inclusive(client):
    data = client.get("/api/products?priceMax=15000&perPage=48").json()
    amounts = [i["price"]["amount"] for i in data["items"]]
    assert amounts and all(a <= 15000 for a in amounts)


def test_products_available_filter(client):
    all_products = client.get("/api/products?perPage=48").json()
    available = client.get("/api/products?available=true&perPage=48").json()
    # Недоступный товар виден без фильтра и скрыт с available=true.
    assert available["meta"]["total"] == all_products["meta"]["total"] - 1
    assert all(i["available"] for i in available["items"])
    assert any(not i["available"] for i in all_products["items"])


def test_products_combined_filters(client):
    data = client.get(
        "/api/products?category=videokarty&available=true&perPage=48"
    ).json()
    assert data["meta"]["total"] == 3


def test_products_empty_result_is_200(client):
    data = client.get("/api/products?q=zzz-nothing-matches").json()
    assert data["meta"]["total"] == 0
    assert data["items"] == []


def test_products_price_min_over_max_is_empty(client):
    data = client.get("/api/products?priceMin=100000&priceMax=1").json()
    assert data["meta"]["total"] == 0


def test_products_bad_params_are_400(client):
    assert client.get("/api/products?page=abc").status_code == 400
    assert client.get("/api/products?page=0").status_code == 400
    assert client.get("/api/products?perPage=100").status_code == 400
    assert client.get("/api/products?priceMin=cheap").status_code == 400


def test_product_by_id(client):
    first = client.get("/api/products").json()["items"][0]
    found = client.get(f"/api/products/{first['id']}")
    assert found.status_code == 200
    assert found.json()["id"] == first["id"]


def test_product_unknown_id_is_404(client):
    assert client.get("/api/products/99999999").status_code == 404
    not_a_number = client.get("/api/products/not-a-number")
    assert not_a_number.status_code == 404
    assert not_a_number.json()["type"] == "/problems/not-found"
