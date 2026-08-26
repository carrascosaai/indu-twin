def test_list_polygons_empty(client, admin_headers):
    resp = client.get("/api/polygons", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_polygon_not_found(client, admin_headers):
    resp = client.get("/api/polygons/999", headers=admin_headers)
    assert resp.status_code == 404


def test_create_and_list_buildings(client, admin_headers, polygon):
    resp = client.post(
        f"/api/polygons/{polygon.id}/buildings",
        headers=admin_headers,
        json={"name": "Nave X", "code": "X1", "lat": 41.0, "lng": -1.0, "area_m2": 500},
    )
    assert resp.status_code == 201
    building_id = resp.json()["id"]
    assert resp.json()["status"] == "normal"

    resp = client.get(f"/api/polygons/{polygon.id}/buildings", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == building_id


def test_new_building_is_provisioned_with_default_sensors(client, admin_headers, polygon):
    resp = client.post(
        f"/api/polygons/{polygon.id}/buildings",
        headers=admin_headers,
        json={"name": "Nave X", "code": "X1", "lat": 41.0, "lng": -1.0, "area_m2": 500},
    )
    building_id = resp.json()["id"]

    resp = client.get(f"/api/buildings/{building_id}/sensors", headers=admin_headers)
    assert resp.status_code == 200
    types = {s["sensor_type"] for s in resp.json()}
    assert types == {"temperature", "energy", "vibration", "humidity"}


def test_viewer_cannot_create_building(client, viewer_headers, polygon):
    resp = client.post(
        f"/api/polygons/{polygon.id}/buildings",
        headers=viewer_headers,
        json={"name": "Nave X", "code": "X1", "lat": 41.0, "lng": -1.0},
    )
    assert resp.status_code == 403


def test_building_dashboard_lists_sensors(client, admin_headers, building, temperature_sensor):
    resp = client.get(f"/api/buildings/{building.id}/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building"]["id"] == building.id
    assert len(data["sensors"]) == 1
    assert data["sensors"][0]["latest_value"] is None


def test_building_not_found(client, admin_headers):
    resp = client.get("/api/buildings/999/dashboard", headers=admin_headers)
    assert resp.status_code == 404


def test_polygon_dashboard_with_no_buildings(client, admin_headers, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_count"] == 0
    assert data["overall_status"] == "normal"
    assert data["active_alerts_count"] == 0


def test_admin_can_delete_building(client, admin_headers, building):
    resp = client.delete(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 204
    resp = client.get(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 404


def test_viewer_cannot_delete_building(client, viewer_headers, building):
    resp = client.delete(f"/api/buildings/{building.id}", headers=viewer_headers)
    assert resp.status_code == 403


def test_deleting_building_cascades_to_sensors(client, admin_headers, building, temperature_sensor):
    resp = client.delete(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 204
    resp = client.get(f"/api/sensors/{temperature_sensor.id}/readings", headers=admin_headers)
    assert resp.status_code == 404


def test_admin_can_delete_polygon(client, admin_headers, polygon, building):
    resp = client.delete(f"/api/polygons/{polygon.id}", headers=admin_headers)
    assert resp.status_code == 204
    resp = client.get(f"/api/polygons/{polygon.id}", headers=admin_headers)
    assert resp.status_code == 404
    resp = client.get(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 404


def test_viewer_cannot_delete_polygon(client, viewer_headers, polygon):
    resp = client.delete(f"/api/polygons/{polygon.id}", headers=viewer_headers)
    assert resp.status_code == 403


def test_new_building_has_no_threshold_overrides(client, admin_headers, building):
    resp = client.get(f"/api/buildings/{building.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["temp_warning"] is None
    assert data["temp_critical"] is None


def test_admin_can_set_building_thresholds(client, admin_headers, building):
    resp = client.patch(
        f"/api/buildings/{building.id}/thresholds",
        headers=admin_headers,
        json={"temp_warning": 40, "temp_critical": 50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["temp_warning"] == 40
    assert data["temp_critical"] == 50
    # El resto de umbrales no se ven afectados y siguen usando el global.
    assert data["vibration_warning"] is None


def test_admin_can_clear_building_thresholds(client, admin_headers, building):
    client.patch(
        f"/api/buildings/{building.id}/thresholds",
        headers=admin_headers,
        json={"temp_warning": 40},
    )
    resp = client.patch(
        f"/api/buildings/{building.id}/thresholds", headers=admin_headers, json={}
    )
    assert resp.status_code == 200
    assert resp.json()["temp_warning"] is None


def test_viewer_cannot_set_building_thresholds(client, viewer_headers, building):
    resp = client.patch(
        f"/api/buildings/{building.id}/thresholds",
        headers=viewer_headers,
        json={"temp_warning": 40},
    )
    assert resp.status_code == 403


def test_set_thresholds_building_not_found(client, admin_headers):
    resp = client.patch(
        "/api/buildings/999/thresholds", headers=admin_headers, json={"temp_warning": 40}
    )
    assert resp.status_code == 404


def test_get_default_thresholds(client, admin_headers):
    resp = client.get("/api/buildings/thresholds/defaults", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["temp_warning"] == 30.0
    assert data["temp_critical"] == 35.0


def test_custom_thresholds_affect_alert_evaluation(
    client, admin_headers, building, temperature_sensor
):
    # Sin umbral personalizado, 32C ya dispara un aviso (umbral global 30C).
    client.patch(
        f"/api/buildings/{building.id}/thresholds",
        headers=admin_headers,
        json={"temp_warning": 40, "temp_critical": 45},
    )
    resp = client.post(
        "/api/ingest/reading",
        json={
            "sensor_id": temperature_sensor.id,
            "api_key": temperature_sensor.api_key,
            "value": 32,
        },
    )
    assert resp.status_code == 201
    resp = client.get(f"/api/buildings/{building.id}/dashboard", headers=admin_headers)
    assert resp.json()["active_alerts"] == []


def test_admin_can_view_sensor_api_key(client, admin_headers, temperature_sensor):
    resp = client.get(
        f"/api/sensors/{temperature_sensor.id}/api-key", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["api_key"] == temperature_sensor.api_key


def test_viewer_cannot_view_sensor_api_key(client, viewer_headers, temperature_sensor):
    resp = client.get(
        f"/api/sensors/{temperature_sensor.id}/api-key", headers=viewer_headers
    )
    assert resp.status_code == 403


def test_admin_can_regenerate_sensor_api_key(client, admin_headers, temperature_sensor):
    old_key = temperature_sensor.api_key
    resp = client.post(
        f"/api/sensors/{temperature_sensor.id}/api-key/regenerate", headers=admin_headers
    )
    assert resp.status_code == 200
    new_key = resp.json()["api_key"]
    assert new_key != old_key

    # La clave vieja deja de servir para ingestar.
    resp = client.post(
        "/api/ingest/reading",
        json={"sensor_id": temperature_sensor.id, "api_key": old_key, "value": 22},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/ingest/reading",
        json={"sensor_id": temperature_sensor.id, "api_key": new_key, "value": 22},
    )
    assert resp.status_code == 201
