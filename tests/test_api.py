import pytest

from app.main import PUBLIC_DIR


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
