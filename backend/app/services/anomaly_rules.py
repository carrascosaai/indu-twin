"""Motor de reglas para deteccion de alertas y anomalias.

Cada regla es una funcion pura: recibe el sensor, el valor nuevo y el
historial reciente, y devuelve None o un dict listo para crear una Alert.
El dia que sustituyamos esto por Machine Learning, solo hay que cambiar
la implementacion de estas funciones manteniendo la misma firma de
entrada/salida, sin tocar el resto de la aplicacion.
"""

from statistics import mean

from app.models import AlertSeverity, AlertType, Building, Sensor, SensorType

# Umbrales por defecto, usados cuando una nave no tiene los suyos propios
# configurados (ver campos opcionales en Building). Ajustables sin tocar
# el resto del codigo.
TEMPERATURE_WARNING = 30.0
TEMPERATURE_CRITICAL = 35.0

VIBRATION_WARNING = 5.0
VIBRATION_CRITICAL = 8.0

HUMIDITY_WARNING = 85.0
HUMIDITY_CRITICAL = 95.0

ENERGY_ANOMALY_WARNING_PCT = 0.40
ENERGY_ANOMALY_CRITICAL_PCT = 0.70
ENERGY_MIN_BASELINE_SAMPLES = 5


def _resolve(override: float | None, default: float) -> float:
    return override if override is not None else default


def _threshold_rule(value: float, warning: float, critical: float, unit: str, label: str):
    if value >= critical:
        return {
            "severity": AlertSeverity.critical,
            "alert_type": AlertType.threshold,
            "message": f"{label} critico: {value:.1f}{unit} (umbral {critical:.1f}{unit})",
            "value": value,
            "threshold": critical,
        }
    if value >= warning:
        return {
            "severity": AlertSeverity.warning,
            "alert_type": AlertType.threshold,
            "message": f"{label} elevado: {value:.1f}{unit} (umbral {warning:.1f}{unit})",
            "value": value,
            "threshold": warning,
        }
    return None


def _format_energy(value: float) -> str:
    """El consumo por lectura puede ser de escala horaria (historico) o de
    pocos segundos (en vivo), asi que se formatea en Wh cuando es muy
    pequeno para no mostrar siempre "0.0 kWh"."""
    if value < 1:
        return f"{value * 1000:.0f} Wh"
    return f"{value:.2f} kWh"


def _energy_anomaly_rule(
    value: float, history_values: list[float], warning_pct: float, critical_pct: float
):
    baseline = [v for v in history_values]
    if len(baseline) < ENERGY_MIN_BASELINE_SAMPLES:
        return None
    baseline_avg = mean(baseline)
    if baseline_avg <= 0:
        return None
    increase_pct = (value - baseline_avg) / baseline_avg
    if increase_pct >= critical_pct:
        return {
            "severity": AlertSeverity.critical,
            "alert_type": AlertType.anomaly,
            "message": (
                f"Consumo anomalo: {_format_energy(value)}, "
                f"{increase_pct * 100:.0f}% por encima de su media habitual "
                f"({_format_energy(baseline_avg)})"
            ),
            "value": value,
            "threshold": baseline_avg,
        }
    if increase_pct >= warning_pct:
        return {
            "severity": AlertSeverity.warning,
            "alert_type": AlertType.anomaly,
            "message": (
                f"Consumo por encima de lo habitual: {_format_energy(value)}, "
                f"{increase_pct * 100:.0f}% sobre su media ({_format_energy(baseline_avg)})"
            ),
            "value": value,
            "threshold": baseline_avg,
        }
    return None


def evaluate_reading(sensor: Sensor, value: float, recent_values: list[float]) -> dict | None:
    """Evalua una lectura nueva contra las reglas del tipo de sensor.

    `recent_values` es el historial reciente del MISMO sensor (sin incluir
    el valor nuevo), usado como linea base para las reglas de anomalia.
    Si la nave tiene umbrales personalizados (`building.temp_warning`,
    etc.) se usan esos; si no, se cae en los valores globales por defecto.
    Devuelve un dict con los campos para crear una Alert, o None.
    """
    building: Building = sensor.building

    if sensor.sensor_type == SensorType.temperature:
        return _threshold_rule(
            value,
            _resolve(building.temp_warning, TEMPERATURE_WARNING),
            _resolve(building.temp_critical, TEMPERATURE_CRITICAL),
            "C",
            "Temperatura",
        )
    if sensor.sensor_type == SensorType.vibration:
        return _threshold_rule(
            value,
            _resolve(building.vibration_warning, VIBRATION_WARNING),
            _resolve(building.vibration_critical, VIBRATION_CRITICAL),
            " mm/s",
            "Vibracion",
        )
    if sensor.sensor_type == SensorType.humidity:
        return _threshold_rule(
            value,
            _resolve(building.humidity_warning, HUMIDITY_WARNING),
            _resolve(building.humidity_critical, HUMIDITY_CRITICAL),
            "%",
            "Humedad",
        )
    if sensor.sensor_type == SensorType.energy:
        return _energy_anomaly_rule(
            value,
            recent_values,
            _resolve(building.energy_anomaly_warning_pct, ENERGY_ANOMALY_WARNING_PCT),
            _resolve(building.energy_anomaly_critical_pct, ENERGY_ANOMALY_CRITICAL_PCT),
        )
    return None
