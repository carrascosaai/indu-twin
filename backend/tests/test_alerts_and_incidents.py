def _active_alerts(client, headers, building_id):
    return client.get(
        "/api/alerts",
        params={"building_id": building_id, "status": "active"},
        headers=headers,
    ).json()


def _ingest(client, sensor, value):
    return client.post(
        "/api/ingest/reading",
        json={"sensor_id": sensor.id, "api_key": sensor.api_key, "value": value},
    )


def test_ingest_above_threshold_creates_alert_and_updates_status(
    client, admin_headers, building, temperature_sensor
):
    resp = _ingest(client, temperature_sensor, 40.0)
    assert resp.status_code == 201

    resp = client.get(f"/api/buildings/{building.id}/dashboard", headers=admin_headers)
    data = resp.json()
    assert data["building"]["status"] == "critical"
    assert len(data["active_alerts"]) == 1
    assert data["active_alerts"][0]["severity"] == "critical"


def test_ingest_normal_value_does_not_create_alert(
    client, admin_headers, building, temperature_sensor
):
    resp = _ingest(client, temperature_sensor, 22.0)
    assert resp.status_code == 201

    resp = client.get(f"/api/buildings/{building.id}/dashboard", headers=admin_headers)
    data = resp.json()
    assert data["building"]["status"] == "normal"
    assert data["active_alerts"] == []


def test_resolve_alert_clears_building_status(
    client, admin_headers, building, temperature_sensor
):
    _ingest(client, temperature_sensor, 40.0)
    alerts = _active_alerts(client, admin_headers, building.id)
    assert len(alerts) == 1
    alert_id = alerts[0]["id"]

    resp = client.patch(f"/api/alerts/{alert_id}/resolve", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    dashboard = client.get(
        f"/api/buildings/{building.id}/dashboard", headers=admin_headers
    ).json()
    assert dashboard["building"]["status"] == "normal"
    assert dashboard["active_alerts"] == []


def test_energy_anomaly_detected_after_baseline(client, admin_headers, building, energy_sensor):
    # Construye una linea base estable
    for value in [5.0, 5.1, 4.9, 5.0, 5.2]:
        _ingest(client, energy_sensor, value)

    # Pico muy por encima de la media -> anomalia
    resp = _ingest(client, energy_sensor, 12.0)
    assert resp.status_code == 201

    alerts = _active_alerts(client, admin_headers, building.id)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "anomaly"


def test_viewer_can_resolve_alerts(client, viewer_headers, building, temperature_sensor):
    _ingest(client, temperature_sensor, 40.0)
    alerts = _active_alerts(client, viewer_headers, building.id)
    alert_id = alerts[0]["id"]

    resp = client.patch(f"/api/alerts/{alert_id}/resolve", headers=viewer_headers)
    assert resp.status_code == 200


def test_create_and_update_incident(client, admin_headers, building):
    resp = client.post(
        f"/api/buildings/{building.id}/incidents",
        headers=admin_headers,
        json={"title": "Fuga de aceite", "priority": "high"},
    )
    assert resp.status_code == 201
    incident = resp.json()
    assert incident["status"] == "open"
    assert incident["resolved_at"] is None

    resp = client.patch(
        f"/api/incidents/{incident['id']}", headers=admin_headers, json={"status": "resolved"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolved_at"] is not None


def test_polygon_incidents_aggregate_across_buildings(
    client, admin_headers, polygon, building
):
    client.post(
        f"/api/buildings/{building.id}/incidents",
        headers=admin_headers,
        json={"title": "Incidencia A"},
    )

    resp = client.get(f"/api/polygons/{polygon.id}/incidents", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Incidencia A"

    resp = client.get(
        f"/api/polygons/{polygon.id}/incidents",
        params={"status": "resolved"},
        headers=admin_headers,
    )
    assert resp.json() == []


def test_incident_requires_existing_building(client, admin_headers):
    resp = client.post(
        "/api/buildings/999/incidents", headers=admin_headers, json={"title": "x"}
    )
    assert resp.status_code == 404
