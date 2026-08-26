def _ingest(client, sensor, value):
    return client.post(
        "/api/ingest/reading",
        json={"sensor_id": sensor.id, "api_key": sensor.api_key, "value": value},
    )


def test_pdf_report_daily(client, admin_headers, polygon, building, temperature_sensor):
    _ingest(client, temperature_sensor, 22.0)
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/daily",
        params={"format": "pdf"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert "attachment" in resp.headers["content-disposition"]


def test_excel_report_weekly(client, admin_headers, polygon, building, temperature_sensor):
    _ingest(client, temperature_sensor, 22.0)
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/weekly",
        params={"format": "xlsx"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # Cabecera de fichero ZIP: un .xlsx es un ZIP de XMLs.
    assert resp.content[:2] == b"PK"


def test_report_defaults_to_pdf(client, admin_headers, polygon, building):
    resp = client.get(f"/api/polygons/{polygon.id}/reports/monthly", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_report_empty_polygon_does_not_crash(client, admin_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/daily",
        params={"format": "pdf"},
        headers=admin_headers,
    )
    assert resp.status_code == 200


def test_report_invalid_period(client, admin_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/yearly",
        params={"format": "pdf"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_report_invalid_format(client, admin_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/daily",
        params={"format": "csv"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_report_polygon_not_found(client, admin_headers):
    resp = client.get(
        "/api/polygons/999/reports/daily", params={"format": "pdf"}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_report_viewer_can_access(client, viewer_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/daily",
        params={"format": "pdf"},
        headers=viewer_headers,
    )
    assert resp.status_code == 200


def test_report_tenant_forbidden(client, tenant_headers, polygon):
    resp = client.get(
        f"/api/polygons/{polygon.id}/reports/daily",
        params={"format": "pdf"},
        headers=tenant_headers,
    )
    assert resp.status_code == 403


def test_report_requires_auth(client, polygon):
    resp = client.get(f"/api/polygons/{polygon.id}/reports/daily", params={"format": "pdf"})
    assert resp.status_code == 401
