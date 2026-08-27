"""Generador de datos simulados realistas y bucle de simulacion en background.

Diseñado para que, cuando haya sensores ESP32 reales, el unico cambio sea
el origen de las lecturas: en vez de `generate_value(...)` se recibiran
por MQTT/HTTP en el endpoint /api/ingest/reading, que reutiliza la misma
funcion `process_new_reading` para aplicar reglas de anomalias.
"""

import asyncio
import logging
import math
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    Building,
    BuildingStatus,
    Sensor,
    SensorReading,
    SensorType,
)
from app.services import notifications
from app.services.anomaly_rules import evaluate_reading

logger = logging.getLogger("indu_twin.simulator")

SPIKE_PROBABILITY = 0.04  # probabilidad de un evento anomalo por sensor y tick, para demo


def _building_profile(building_id: int) -> dict:
    """Perfil determinista por nave: algunas consumen/calientan mas que otras."""
    rng = random.Random(building_id * 7919)
    return {
        "energy_scale": rng.uniform(0.6, 1.8),
        "temp_offset": rng.uniform(-2.0, 4.0),
        "vibration_scale": rng.uniform(0.7, 1.5),
    }


def generate_value(
    sensor_type: SensorType,
    building_id: int,
    timestamp: datetime,
    force_spike: bool = False,
    interval_seconds: float = 3600,
) -> float:
    profile = _building_profile(building_id)
    hour = timestamp.hour + timestamp.minute / 60.0
    is_weekday = timestamp.weekday() < 5

    if sensor_type == SensorType.temperature:
        # patron diurno: minimo de madrugada, maximo a media tarde
        diurnal = 8.5 * math.sin(math.pi * (hour - 6) / 14) if 6 <= hour <= 20 else -2
        base = 21 + diurnal + profile["temp_offset"]
        noise = random.gauss(0, 0.6)
        value = base + noise
        if force_spike:
            value += random.uniform(8, 14)
        return round(max(15, min(45, value)), 1)

    if sensor_type == SensorType.energy:
        # Potencia media (~kWh si se mantuviera una hora), mayor en horario
        # laboral entre semana. Se escala por la duracion real del intervalo
        # para que el consumo acumulado sea correcto tanto en el historico
        # (intervalos de 1h) como en vivo (intervalos de pocos segundos).
        if is_weekday and 8 <= hour <= 18:
            occupancy = 1.0
        elif is_weekday and (6 <= hour < 8 or 18 < hour <= 21):
            occupancy = 0.5
        else:
            occupancy = 0.15
        hourly_rate = 4.0 * occupancy * profile["energy_scale"]
        noise = random.gauss(0, 0.3 * profile["energy_scale"])
        scale = interval_seconds / 3600
        value = max(0.02 * scale, (hourly_rate + noise) * scale)
        if force_spike:
            value *= random.uniform(1.6, 2.4)
        return round(value, 4)

    if sensor_type == SensorType.vibration:
        base = 1.2 * profile["vibration_scale"]
        noise = abs(random.gauss(0, 0.5))
        value = base + noise
        if force_spike:
            value += random.uniform(5, 9)
        return round(max(0, value), 2)

    if sensor_type == SensorType.humidity:
        base = 55 + 10 * math.sin(math.pi * (hour - 3) / 12)
        noise = random.gauss(0, 3)
        value = base + noise
        if force_spike:
            value += random.uniform(20, 35)
        return round(max(20, min(100, value)), 1)

    raise ValueError(f"Tipo de sensor desconocido: {sensor_type}")


def _recent_values(db: Session, sensor_id: int, limit: int = 20) -> list[float]:
    rows = db.execute(
        select(SensorReading.value)
        .where(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
    ).all()
    return [r[0] for r in rows]


def update_building_status(db: Session, building: Building) -> None:
    worst = db.execute(
        select(Alert.severity)
        .where(Alert.building_id == building.id, Alert.status == AlertStatus.active)
    ).all()
    severities = {row[0] for row in worst}
    if "critical" in {s.value if hasattr(s, "value") else s for s in severities}:
        building.status = BuildingStatus.critical
    elif "warning" in {s.value if hasattr(s, "value") else s for s in severities}:
        building.status = BuildingStatus.warning
    else:
        building.status = BuildingStatus.normal


def process_new_reading(
    db: Session, sensor: Sensor, value: float, timestamp: datetime | None = None
) -> SensorReading:
    """Guarda una lectura, aplica las reglas de anomalias y actualiza alertas/estado.

    Punto de entrada unico usado tanto por el simulador como por el futuro
    endpoint de ingesta de sensores reales.
    """
    ts = timestamp or datetime.now(UTC)
    history = _recent_values(db, sensor.id)

    reading = SensorReading(sensor_id=sensor.id, value=value, timestamp=ts)
    db.add(reading)

    rule_result = evaluate_reading(sensor, value, history)
    building = sensor.building

    # En condiciones normales solo hay una alerta activa por sensor, pero
    # una carrera entre dos escrituras concurrentes (ingesta real + simulador,
    # por ejemplo) podria crear mas de una. Nos quedamos con la mas reciente
    # como canonica y resolvemos el resto para no romper el resto del tick.
    active_alerts = db.execute(
        select(Alert)
        .where(Alert.sensor_id == sensor.id, Alert.status == AlertStatus.active)
        .order_by(Alert.created_at.desc())
    ).scalars().all()
    existing_active = active_alerts[0] if active_alerts else None
    for stale in active_alerts[1:]:
        stale.status = AlertStatus.resolved
        stale.resolved_at = ts

    # Solo se notifica por email al pasar A critico (alta nueva o escalada
    # desde warning), nunca en cada tick que la reevalua: si no, un sensor
    # atascado en critico mandaria un correo cada pocos segundos.
    alert_to_notify: Alert | None = None

    if rule_result:
        if existing_active:
            became_critical = (
                rule_result["severity"] == AlertSeverity.critical
                and existing_active.severity != AlertSeverity.critical
            )
            existing_active.severity = rule_result["severity"]
            existing_active.message = rule_result["message"]
            existing_active.value = rule_result["value"]
            existing_active.threshold = rule_result["threshold"]
            if became_critical:
                alert_to_notify = existing_active
        else:
            alert = Alert(
                building_id=building.id,
                sensor_id=sensor.id,
                severity=rule_result["severity"],
                alert_type=rule_result["alert_type"],
                message=rule_result["message"],
                value=rule_result["value"],
                threshold=rule_result["threshold"],
                status=AlertStatus.active,
            )
            db.add(alert)
            if rule_result["severity"] == AlertSeverity.critical:
                alert_to_notify = alert
    elif existing_active:
        existing_active.status = AlertStatus.resolved
        existing_active.resolved_at = ts

    db.flush()
    update_building_status(db, building)

    if alert_to_notify is not None:
        notifications.notify_critical_alert(db, alert_to_notify, building)

    return reading


def run_simulation_tick(
    db: Session, timestamp: datetime | None = None, interval_seconds: float | None = None
) -> int:
    ts = timestamp or datetime.now(UTC)
    interval = interval_seconds or settings.simulation_interval_seconds
    # Los sensores que ya reciben lecturas reales (is_simulated=False, ver
    # app/routers/ingest.py) no se tocan: mezclar aqui datos falsos con los
    # reales que manda el dispositivo fisico rompería las alertas.
    sensors = db.execute(select(Sensor).where(Sensor.is_simulated.is_(True))).scalars().all()
    count = 0
    for sensor in sensors:
        # SAVEPOINT por sensor: si uno falla, solo se descarta su cambio,
        # sin tumbar el progreso ya hecho para el resto en este mismo tick.
        try:
            with db.begin_nested():
                force_spike = random.random() < SPIKE_PROBABILITY
                value = generate_value(
                    sensor.sensor_type,
                    sensor.building_id,
                    ts,
                    force_spike,
                    interval_seconds=interval,
                )
                process_new_reading(db, sensor, value, ts)
            count += 1
        except Exception:
            logger.exception("Error procesando el sensor %s, se omite este tick", sensor.id)
    db.commit()
    return count


async def simulation_loop() -> None:
    interval = settings.simulation_interval_seconds
    logger.info("Simulador iniciado (intervalo=%ss)", interval)
    while True:
        try:
            db = SessionLocal()
            try:
                n = run_simulation_tick(db)
                logger.debug("Tick de simulacion: %s lecturas generadas", n)
            finally:
                db.close()
        except Exception:
            logger.exception("Error en el tick de simulacion")
        await asyncio.sleep(interval)


def backfill_history(db: Session, days: int = 7, step_minutes: int = 60) -> None:
    """Genera historico realista hacia atras en el tiempo, para que los
    graficos tengan datos nada mas arrancar (sin esperar al tiempo real)."""
    sensors = db.execute(select(Sensor)).scalars().all()
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    total_steps = int(days * 24 * 60 / step_minutes)

    interval_seconds = step_minutes * 60
    for sensor in sensors:
        ts = start
        for _ in range(total_steps):
            force_spike = random.random() < SPIKE_PROBABILITY / 3
            value = generate_value(
                sensor.sensor_type,
                sensor.building_id,
                ts,
                force_spike,
                interval_seconds=interval_seconds,
            )
            db.add(SensorReading(sensor_id=sensor.id, value=value, timestamp=ts))
            ts += timedelta(minutes=step_minutes)
    db.commit()
