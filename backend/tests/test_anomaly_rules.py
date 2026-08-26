from app.models import Building, Sensor, SensorType
from app.services.anomaly_rules import evaluate_reading


def _sensor(sensor_type: SensorType, building: Building | None = None) -> Sensor:
    sensor = Sensor(id=1, building_id=1, sensor_type=sensor_type, name="s", unit="u")
    # Sin umbrales personalizados por defecto: usa los globales.
    sensor.building = building or Building(id=1, polygon_id=1, name="b", code="B1", lat=0, lng=0)
    return sensor


def test_temperature_below_threshold_is_fine():
    assert evaluate_reading(_sensor(SensorType.temperature), 25.0, []) is None


def test_temperature_warning_threshold():
    result = evaluate_reading(_sensor(SensorType.temperature), 31.0, [])
    assert result is not None
    assert result["severity"] == "warning"


def test_temperature_critical_threshold():
    result = evaluate_reading(_sensor(SensorType.temperature), 36.0, [])
    assert result is not None
    assert result["severity"] == "critical"


def test_vibration_thresholds():
    assert evaluate_reading(_sensor(SensorType.vibration), 2.0, []) is None
    assert evaluate_reading(_sensor(SensorType.vibration), 6.0, [])["severity"] == "warning"
    assert evaluate_reading(_sensor(SensorType.vibration), 9.0, [])["severity"] == "critical"


def test_humidity_thresholds():
    assert evaluate_reading(_sensor(SensorType.humidity), 60.0, []) is None
    assert evaluate_reading(_sensor(SensorType.humidity), 90.0, [])["severity"] == "warning"
    assert evaluate_reading(_sensor(SensorType.humidity), 96.0, [])["severity"] == "critical"


def test_energy_anomaly_needs_enough_history():
    # Con poco historico no se puede establecer una linea base fiable
    result = evaluate_reading(_sensor(SensorType.energy), 20.0, [5.0, 5.0])
    assert result is None


def test_energy_anomaly_warning_on_moderate_spike():
    baseline = [5.0, 5.1, 4.9, 5.0, 5.0]
    result = evaluate_reading(_sensor(SensorType.energy), 7.2, baseline)  # +44% approx
    assert result is not None
    assert result["severity"] == "warning"
    assert result["alert_type"] == "anomaly"


def test_energy_anomaly_critical_on_large_spike():
    baseline = [5.0, 5.1, 4.9, 5.0, 5.0]
    result = evaluate_reading(_sensor(SensorType.energy), 9.0, baseline)  # +80% approx
    assert result is not None
    assert result["severity"] == "critical"


def test_energy_no_anomaly_when_within_normal_range():
    baseline = [5.0, 5.1, 4.9, 5.0, 5.0]
    result = evaluate_reading(_sensor(SensorType.energy), 5.2, baseline)
    assert result is None
