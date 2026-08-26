from app.config import settings


def _set_plan(monkeypatch, plan):
    monkeypatch.setattr(settings, "plan", plan)


def test_plan_status_reflects_usage(client, admin_headers, polygon, building):
    resp = client.get("/api/plan", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["polygons"]["used"] == 1
    assert data["polygons"]["limit"] == 1
    assert data["buildings"]["used"] == 1
    assert data["buildings"]["limit"] == 3


def test_free_plan_blocks_second_polygon(client, admin_headers, polygon):
    resp = client.post(
        "/api/polygons",
        headers=admin_headers,
        json={"name": "Otro", "center_lat": 40.0, "center_lng": -3.0},
    )
    assert resp.status_code == 402


def test_free_plan_blocks_fourth_building(client, admin_headers, polygon):
    for i in range(3):
        resp = client.post(
            f"/api/polygons/{polygon.id}/buildings",
            headers=admin_headers,
            json={"name": f"Nave {i}", "code": f"N{i}", "lat": 41.0, "lng": -1.0},
        )
        assert resp.status_code == 201

    resp = client.post(
        f"/api/polygons/{polygon.id}/buildings",
        headers=admin_headers,
        json={"name": "Nave extra", "code": "NX", "lat": 41.0, "lng": -1.0},
    )
    assert resp.status_code == 402


def test_free_plan_blocks_third_user(client, admin_headers, admin_user, viewer_user):
    # admin_user + viewer_user ya son 2 (limite free), el siguiente debe fallar.
    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "third@test.com",
            "password": "pass1234",
            "full_name": "Third",
            "role": "viewer",
        },
    )
    assert resp.status_code == 402


def test_pro_plan_allows_more_polygons(monkeypatch, client, admin_headers, polygon):
    _set_plan(monkeypatch, "pro")
    resp = client.post(
        "/api/polygons",
        headers=admin_headers,
        json={"name": "Otro", "center_lat": 40.0, "center_lng": -3.0},
    )
    assert resp.status_code == 201


def test_business_plan_is_unlimited(monkeypatch, client, admin_headers, polygon):
    _set_plan(monkeypatch, "business")
    for i in range(5):
        resp = client.post(
            "/api/polygons",
            headers=admin_headers,
            json={"name": f"Otro {i}", "center_lat": 40.0, "center_lng": -3.0},
        )
        assert resp.status_code == 201


def test_unknown_plan_value_falls_back_to_free(monkeypatch, client, admin_headers, polygon):
    _set_plan(monkeypatch, "not-a-real-plan")
    resp = client.get("/api/plan", headers=admin_headers)
    assert resp.json()["plan"] == "free"
