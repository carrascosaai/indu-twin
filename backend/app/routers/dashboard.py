from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import forbid_tenant, get_current_user, get_db
from app.services.efficiency import efficiency_scores, kwh_per_m2
from app.services.prediction import predict_next_24h
from app.services.timeseries import bucket_readings

router = APIRouter(
    prefix="/api/polygons", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


def energy_totals_24h(db: Session, buildings: list[models.Building]) -> dict[int, float]:
    """Suma de consumo (kWh) de las ultimas 24h por nave. Reutilizado por el
    dashboard del poligono y el de cada nave individual para calcular
    eficiencia de forma consistente."""
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    totals: dict[int, float] = {}
    for b in buildings:
        energy_ids = db.execute(
            select(models.Sensor.id).where(
                models.Sensor.building_id == b.id,
                models.Sensor.sensor_type == models.SensorType.energy,
            )
        ).scalars().all()
        total = 0.0
        if energy_ids:
            total = db.execute(
                select(func.coalesce(func.sum(models.SensorReading.value), 0.0)).where(
                    models.SensorReading.sensor_id.in_(energy_ids),
                    models.SensorReading.timestamp >= since_24h,
                )
            ).scalar_one()
        totals[b.id] = total
    return totals


def predict_energy(
    db: Session, sensor_ids: list[int], now: datetime, days: int = 7
) -> tuple[float | None, list[schemas.SeriesPoint]]:
    """Prediccion de consumo (kWh) para las proximas 24h, a partir del
    perfil horario promedio de los ultimos `days` dias."""
    if not sensor_ids:
        return None, []

    since = now - timedelta(days=days)
    rows = bucket_readings(db, sensor_ids, since, granularity="hour", agg="sum")
    hourly_totals = [(bucket.hour, total) for bucket, total in rows]

    total, series = predict_next_24h(hourly_totals, now)
    if total is None:
        return None, []
    return total, [schemas.SeriesPoint(timestamp=ts, value=v) for ts, v in series]


def _overall_status(building_statuses: list[models.BuildingStatus]) -> models.BuildingStatus:
    if any(s == models.BuildingStatus.critical for s in building_statuses):
        return models.BuildingStatus.critical
    if any(s == models.BuildingStatus.warning for s in building_statuses):
        return models.BuildingStatus.warning
    return models.BuildingStatus.normal


@router.get(
    "/{polygon_id}/dashboard",
    response_model=schemas.PolygonDashboardOut,
    dependencies=[Depends(forbid_tenant)],
)
def polygon_dashboard(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")

    buildings = db.execute(
        select(models.Building).where(models.Building.polygon_id == polygon_id)
    ).scalars().all()
    building_ids = [b.id for b in buildings]

    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)

    if building_ids:
        energy_sensor_ids = db.execute(
            select(models.Sensor.id).where(
                models.Sensor.building_id.in_(building_ids),
                models.Sensor.sensor_type == models.SensorType.energy,
            )
        ).scalars().all()
        temp_sensor_ids = db.execute(
            select(models.Sensor.id).where(
                models.Sensor.building_id.in_(building_ids),
                models.Sensor.sensor_type == models.SensorType.temperature,
            )
        ).scalars().all()
    else:
        energy_sensor_ids, temp_sensor_ids = [], []

    total_energy_24h = 0.0
    energy_series: list[schemas.SeriesPoint] = []
    if energy_sensor_ids:
        total_energy_24h = db.execute(
            select(func.coalesce(func.sum(models.SensorReading.value), 0.0)).where(
                models.SensorReading.sensor_id.in_(energy_sensor_ids),
                models.SensorReading.timestamp >= since_24h,
            )
        ).scalar_one()

        rows = bucket_readings(db, energy_sensor_ids, since_24h, granularity="hour", agg="sum")
        energy_series = [
            schemas.SeriesPoint(timestamp=b, value=round(v, 2)) for b, v in rows
        ]

    temperature_series: list[schemas.SeriesPoint] = []
    if temp_sensor_ids:
        rows = bucket_readings(db, temp_sensor_ids, since_24h, granularity="hour", agg="avg")
        temperature_series = [
            schemas.SeriesPoint(timestamp=b, value=round(v, 1)) for b, v in rows
        ]

    building_totals = energy_totals_24h(db, buildings)

    efficiency_values = {
        b.id: kwh_per_m2(building_totals[b.id], b.area_m2) for b in buildings
    }
    scores = efficiency_scores(efficiency_values)

    ranking = [
        schemas.BuildingRankingItem(
            building_id=b.id,
            name=b.name,
            total_energy_kwh=round(building_totals[b.id], 2),
            efficiency_kwh_per_m2=(
                round(efficiency_values[b.id], 3) if efficiency_values[b.id] is not None else None
            ),
            efficiency_score=scores[b.id],
        )
        for b in buildings
    ]
    ranking.sort(key=lambda r: r.total_energy_kwh, reverse=True)

    previous_energy_24h = 0.0
    if energy_sensor_ids:
        previous_energy_24h = db.execute(
            select(func.coalesce(func.sum(models.SensorReading.value), 0.0)).where(
                models.SensorReading.sensor_id.in_(energy_sensor_ids),
                models.SensorReading.timestamp >= since_48h,
                models.SensorReading.timestamp < since_24h,
            )
        ).scalar_one()
    energy_trend_pct = None
    if previous_energy_24h > 0:
        energy_trend_pct = round(
            (total_energy_24h - previous_energy_24h) / previous_energy_24h * 100, 1
        )

    predicted_total, predicted_series = predict_energy(db, energy_sensor_ids, now)

    active_alerts_count = 0
    recent_alerts: list[models.Alert] = []
    if building_ids:
        active_alerts_count = db.execute(
            select(func.count(models.Alert.id)).where(
                models.Alert.building_id.in_(building_ids),
                models.Alert.status == models.AlertStatus.active,
            )
        ).scalar_one()
        recent_alerts = db.execute(
            select(models.Alert)
            .where(models.Alert.building_id.in_(building_ids))
            .order_by(models.Alert.created_at.desc())
            .limit(10)
        ).scalars().all()

    return schemas.PolygonDashboardOut(
        polygon=polygon,
        building_count=len(buildings),
        total_energy_kwh_24h=round(total_energy_24h, 2),
        energy_trend_pct=energy_trend_pct,
        predicted_energy_kwh_24h=predicted_total,
        active_alerts_count=active_alerts_count,
        overall_status=_overall_status([b.status for b in buildings]),
        energy_series=energy_series,
        temperature_series=temperature_series,
        predicted_energy_series=predicted_series,
        ranking=ranking,
        recent_alerts=recent_alerts,
    )

