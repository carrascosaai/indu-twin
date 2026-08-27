from datetime import UTC, datetime

from app.services.simulator import run_simulation_tick


def _ingest(client, sensor, value):
    return client.post(
        "/api/ingest/reading",
        json={"sensor_id": sensor.id, "api_key": sensor.api_key, "value": value},
    )


def test_sensor_starts_as_simulated(client, admin_headers, building, temperature_sensor):
    resp = client.get(f"/api/buildings/{building.id}/sensors", headers=admin_headers)
    sensor = next(s for s in resp.json() if s["id"] == temperature_sensor.id)
    assert sensor["is_simulated"] is True


def test_real_reading_flips_sensor_to_not_simulated(
    client, admin_headers, building, temperature_sensor
):
    resp = _ingest(client, temperature_sensor, 22.0)
    assert resp.status_code == 201

    resp = client.get(f"/api/buildings/{building.id}/sensors", headers=admin_headers)
    sensor = next(s for s in resp.json() if s["id"] == temperature_sensor.id)
    assert sensor["is_simulated"] is False


def test_simulator_skips_sensors_with_real_data(db_session, temperature_sensor, client):
    _ingest(client, temperature_sensor, 22.0)
    db_session.refresh(temperature_sensor)
    assert temperature_sensor.is_simulated is False

    readings_before = len(temperature_sensor.readings)
    run_simulation_tick(db_session, timestamp=datetime.now(UTC))
    db_session.refresh(temperature_sensor)

    # El tick de simulacion no debe haber añadido una lectura de mentira al
    # sensor que ya recibe datos reales.
    assert len(temperature_sensor.readings) == readings_before


def test_simulator_still_generates_for_untouched_sensors(db_session, temperature_sensor):
    assert temperature_sensor.is_simulated is True
    n = run_simulation_tick(db_session, timestamp=datetime.now(UTC))
    assert n >= 1
