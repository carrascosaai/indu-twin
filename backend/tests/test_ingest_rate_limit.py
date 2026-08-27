from app.routers.ingest import INGEST_MAX_REQUESTS


def _ingest(client, sensor, value=22.0):
    return client.post(
        "/api/ingest/reading",
        json={"sensor_id": sensor.id, "api_key": sensor.api_key, "value": value},
    )


def test_allows_requests_under_the_limit(client, temperature_sensor):
    for _ in range(INGEST_MAX_REQUESTS):
        resp = _ingest(client, temperature_sensor)
        assert resp.status_code == 201


def test_blocks_once_the_limit_is_exceeded(client, temperature_sensor):
    for _ in range(INGEST_MAX_REQUESTS):
        _ingest(client, temperature_sensor)

    resp = _ingest(client, temperature_sensor)
    assert resp.status_code == 429


def test_limit_is_per_sensor_not_global(client, temperature_sensor, energy_sensor):
    for _ in range(INGEST_MAX_REQUESTS):
        _ingest(client, temperature_sensor)
    # El otro sensor de la misma nave no deberia verse afectado.
    resp = _ingest(client, energy_sensor, value=1.0)
    assert resp.status_code == 201


def test_rate_limit_is_checked_before_validating_credentials(client, temperature_sensor):
    """El limite protege el endpoint incluso contra peticiones con api_key
    invalida repetidas contra el mismo sensor_id."""
    for _ in range(INGEST_MAX_REQUESTS):
        client.post(
            "/api/ingest/reading",
            json={"sensor_id": temperature_sensor.id, "api_key": "wrong", "value": 1.0},
        )
    resp = client.post(
        "/api/ingest/reading",
        json={"sensor_id": temperature_sensor.id, "api_key": "wrong", "value": 1.0},
    )
    assert resp.status_code == 429
