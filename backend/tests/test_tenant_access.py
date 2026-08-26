def test_tenant_can_see_own_building(client, tenant_headers, building):
    resp = client.get(f"/api/buildings/{building.id}", headers=tenant_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == building.id


def test_tenant_cannot_see_other_building(client, tenant_headers, other_building):
    resp = client.get(f"/api/buildings/{other_building.id}", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_cannot_see_other_building_dashboard(client, tenant_headers, other_building):
    resp = client.get(f"/api/buildings/{other_building.id}/dashboard", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_can_see_own_building_dashboard(client, tenant_headers, building):
    resp = client.get(f"/api/buildings/{building.id}/dashboard", headers=tenant_headers)
    assert resp.status_code == 200


def test_tenant_cannot_list_polygon_buildings(client, tenant_headers, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}/buildings", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_cannot_list_polygons(client, tenant_headers):
    resp = client.get("/api/polygons", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_cannot_get_polygon(client, tenant_headers, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_cannot_see_polygon_dashboard(client, tenant_headers, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}/dashboard", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_alerts_are_scoped_to_own_building(
    client, tenant_headers, admin_headers, building, other_building, temperature_sensor
):
    resp = client.post(
        "/api/ingest/reading",
        json={
            "sensor_id": temperature_sensor.id,
            "api_key": temperature_sensor.api_key,
            "value": 36,
        },
    )
    assert resp.status_code == 201

    resp = client.get("/api/alerts", headers=tenant_headers)
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["building_id"] == building.id


def test_tenant_alerts_ignore_polygon_id_filter_of_other_building(
    client, tenant_headers, other_building
):
    # Aunque pida explicitamente el poligono/nave de otro, se ignora y se
    # devuelve solo lo de su propia nave (vacio en este caso, sin datos).
    resp = client.get(
        "/api/alerts",
        headers=tenant_headers,
        params={"polygon_id": other_building.polygon_id, "building_id": other_building.id},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_tenant_cannot_resolve_alert_of_other_building(
    client, tenant_headers, admin_headers, other_building, db_session
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    alert = Alert(
        building_id=other_building.id,
        severity=AlertSeverity.warning,
        alert_type=AlertType.threshold,
        message="test",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    resp = client.patch(f"/api/alerts/{alert.id}/resolve", headers=tenant_headers)
    assert resp.status_code == 403


def test_tenant_can_create_incident_for_own_building(client, tenant_headers, building):
    resp = client.post(
        f"/api/buildings/{building.id}/incidents",
        headers=tenant_headers,
        json={"title": "Fuga de agua"},
    )
    assert resp.status_code == 201


def test_tenant_cannot_create_incident_for_other_building(client, tenant_headers, other_building):
    resp = client.post(
        f"/api/buildings/{other_building.id}/incidents",
        headers=tenant_headers,
        json={"title": "No deberia poder"},
    )
    assert resp.status_code == 403


def test_tenant_cannot_export_other_building_readings(client, tenant_headers, other_building):
    resp = client.get(
        f"/api/buildings/{other_building.id}/export/readings.csv", headers=tenant_headers
    )
    assert resp.status_code == 403


def test_tenant_cannot_export_polygon_alerts(client, tenant_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/export/alerts.csv", headers=tenant_headers
    )
    assert resp.status_code == 403


def test_admin_creates_tenant_requires_building(client, admin_headers):
    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "newtenant@test.com",
            "password": "pass1234",
            "full_name": "New Tenant",
            "role": "tenant",
        },
    )
    assert resp.status_code == 400


def test_admin_creates_tenant_with_building(client, admin_headers, building):
    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "newtenant@test.com",
            "password": "pass1234",
            "full_name": "New Tenant",
            "role": "tenant",
            "building_id": building.id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["building_id"] == building.id


def test_admin_promotes_tenant_to_viewer_clears_building(client, admin_headers, tenant_user):
    resp = client.patch(
        f"/api/users/{tenant_user.id}", headers=admin_headers, json={"role": "viewer"}
    )
    assert resp.status_code == 200
    assert resp.json()["building_id"] is None


def test_list_all_buildings_admin_only(client, admin_headers, viewer_headers, building):
    resp = client.get("/api/buildings", headers=admin_headers)
    assert resp.status_code == 200
    assert any(b["id"] == building.id for b in resp.json())

    resp = client.get("/api/buildings", headers=viewer_headers)
    assert resp.status_code == 403


def test_deleting_building_unassigns_tenant(client, admin_headers, tenant_user, building):
    resp = client.delete(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 204

    resp = client.get("/api/users", headers=admin_headers)
    tenant = next(u for u in resp.json() if u["id"] == tenant_user.id)
    assert tenant["building_id"] is None
