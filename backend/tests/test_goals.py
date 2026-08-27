from datetime import UTC, datetime, timedelta

from app.models import SensorReading


def test_admin_can_create_goal(client, admin_headers, polygon, building, energy_sensor):
    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "Bajar consumo 10%", "target_reduction_pct": 10},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Bajar consumo 10%"
    assert data["target_reduction_pct"] == 10
    assert data["polygon_id"] == polygon.id
    assert data["building_id"] is None
    assert data["progress_pct"] >= 0


def test_viewer_cannot_create_goal(client, viewer_headers, polygon):
    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "x", "target_reduction_pct": 10},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_tenant_cannot_list_goals(client, tenant_headers, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}/goals", headers=tenant_headers)
    assert resp.status_code == 403


def test_rejects_out_of_range_reduction(client, admin_headers, polygon):
    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "x", "target_reduction_pct": 150},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_goal_for_building_not_in_polygon_is_rejected(
    client, admin_headers, polygon, db_session
):
    from app.models import Building, Polygon

    other_polygon = Polygon(name="Otro", center_lat=0, center_lng=0)
    db_session.add(other_polygon)
    db_session.flush()
    foreign_building = Building(
        polygon_id=other_polygon.id, name="Ajena", code="X1", lat=0, lng=0, area_m2=100
    )
    db_session.add(foreign_building)
    db_session.commit()

    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "x", "target_reduction_pct": 10, "building_id": foreign_building.id},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_progress_reflects_actual_consumption(
    client, admin_headers, db_session, polygon, building, energy_sensor
):
    now = datetime.now(UTC)
    # Consumo base: 100 kWh/dia durante los 10 dias anteriores a crear el objetivo.
    for i in range(10):
        db_session.add(
            SensorReading(
                sensor_id=energy_sensor.id, value=100.0, timestamp=now - timedelta(days=10 - i)
            )
        )
    db_session.commit()

    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "Bajar 20%", "target_reduction_pct": 20, "duration_days": 30},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    goal = resp.json()
    assert goal["baseline_kwh"] == 1000.0  # 10 dias * 100 kWh

    # Justo despues de crear el objetivo, apenas ha pasado tiempo: progreso
    # deberia estar cerca de 0 sin penalizar (no ha habido tiempo de fallar).
    assert 0 <= goal["progress_pct"] <= 100
    assert goal["is_on_track"] is True


def test_delete_goal(client, admin_headers, polygon, building, energy_sensor):
    resp = client.post(
        f"/api/polygons/{polygon.id}/goals",
        json={"title": "x", "target_reduction_pct": 10},
        headers=admin_headers,
    )
    goal_id = resp.json()["id"]

    del_resp = client.delete(f"/api/goals/{goal_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    list_resp = client.get(f"/api/polygons/{polygon.id}/goals", headers=admin_headers)
    assert all(g["id"] != goal_id for g in list_resp.json())
