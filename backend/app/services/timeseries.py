"""Agregacion de series temporales de lecturas de sensores por hora o dia.

Se hace en Python, no en SQL (nada de `strftime`/`date_trunc`), a proposito:
la version anterior usaba `func.strftime`, que es exclusivo de SQLite y
habria roto en cuanto el backend se conectara a Postgres (ver migracion a
base de datos persistente). En vez de mantener dos variantes de cada query
segun el motor, se trae la ventana de lecturas (que para el tamano de esta
plataforma - un puñado de naves por poligono - es un volumen pequeño) y se
agrupa aqui, de forma identica sea cual sea la base de datos.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def bucket_readings(
    db: Session,
    sensor_ids: list[int],
    since: datetime,
    granularity: str,
    agg: str = "sum",
    until: datetime | None = None,
) -> list[tuple[datetime, float]]:
    """Agrupa las lecturas de `sensor_ids` en `since`..`until` por hora o
    dia (`granularity`: "hour" | "day"), sumando o promediando segun `agg`.
    Devuelve pares (inicio_del_bucket, valor) ordenados cronologicamente."""
    if not sensor_ids:
        return []

    conditions = [
        models.SensorReading.sensor_id.in_(sensor_ids),
        models.SensorReading.timestamp >= since,
    ]
    if until is not None:
        conditions.append(models.SensorReading.timestamp < until)

    rows = db.execute(
        select(models.SensorReading.timestamp, models.SensorReading.value)
        .where(*conditions)
        .order_by(models.SensorReading.timestamp)
    ).all()

    buckets: dict[datetime, list[float]] = {}
    for ts, value in rows:
        # SQLite no conserva el tzinfo al leer de vuelta un DateTime aunque
        # la columna sea timezone=True (a diferencia de Postgres) - se
        # asume UTC para que las claves de bucket sean consistentes.
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if granularity == "hour":
            key = ts.replace(minute=0, second=0, microsecond=0)
        else:
            key = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets.setdefault(key, []).append(value)

    result = []
    for key in sorted(buckets):
        values = buckets[key]
        agg_value = sum(values) if agg == "sum" else sum(values) / len(values)
        result.append((key, agg_value))
    return result
