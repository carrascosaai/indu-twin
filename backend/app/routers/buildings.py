from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import check_building_access, forbid_tenant, get_current_user, get_db, require_admin
from app.routers.dashboard import energy_totals_24h, predict_energy
from app.services import anomaly_rules
from app.services.efficiency import efficiency_scores, kwh_per_m2
from app.services.maintenance import maintenance_risk_score, risk_label
from app.services.plans import check_limit, current_limits, current_plan_name

router = APIRouter(tags=["buildings"], dependencies=[Depends(get_current_user)])


def _sensor_latest(db: Session, sensor: models.Sensor) -> schemas.SensorLatest:
    latest = db.execute(
        select(models.SensorReading)
        .where(models.SensorReading.sensor_id == sensor.id)
        .order_by(models.SensorReading.timestamp.desc())
        .limit(1)
    ).scalar_one_or_none()
    return schemas.SensorLatest(
        id=sensor.id,
        building_id=sensor.building_id,
        sensor_type=sensor.sensor_type,
        name=sensor.name,
        unit=sensor.unit,
        is_simulated=sensor.is_simulated,
        latest_value=latest.value if latest else None,
        latest_timestamp=latest.timestamp if latest else None,
    )


@router.get(
    "/api/polygons/{polygon_id}/buildings",
    response_model=list[schemas.BuildingOut],
    dependencies=[Depends(forbid_tenant)],
)
def list_buildings(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    return db.execute(
        select(models.Building).where(models.Building.polygon_id == polygon_id)
    ).scalars().all()


@router.post(
    "/api/polygons/{polygon_id}/buildings",
    response_model=schemas.BuildingOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_building(
    polygon_id: int, payload: schemas.BuildingCreate, db: Session = Depends(get_db)
):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")

    used = db.execute(select(func.count(models.Building.id))).scalar_one()
    check_limit(used, current_limits().max_buildings, "naves", current_plan_name())

    building = models.Building(polygon_id=polygon_id, **payload.model_dump())
    db.add(building)
    db.flush()
    for sensor_type, name, unit in models.DEFAULT_SENSOR_TEMPLATES:
        db.add(
            models.Sensor(
                building_id=building.id, sensor_type=sensor_type, name=name, unit=unit
            )
        )
    db.commit()
    db.refresh(building)
    return building


@router.delete(
    "/api/buildings/{building_id}", status_code=204, dependencies=[Depends(require_admin)]
)
def delete_building(building_id: int, db: Session = Depends(get_db)):
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    # Las cuentas de empresa asignadas a esta nave se quedan sin nave (no se
    # borran): un admin puede reasignarlas despues a otra nave.
    db.execute(
        update(models.User)
        .where(models.User.building_id == building_id)
        .values(building_id=None)
    )
    db.delete(building)
    db.commit()


@router.get(
    "/api/buildings",
    response_model=list[schemas.BuildingWithPolygonOut],
    dependencies=[Depends(require_admin)],
)
def list_all_buildings(db: Session = Depends(get_db)):
    """Todas las naves de todos los poligonos, con el nombre del poligono al
    que pertenecen. Solo para admins: se usa para asignar una nave a una
    cuenta de empresa (tenant) desde la gestion de usuarios."""
    rows = db.execute(
        select(models.Building, models.Polygon.name)
        .join(models.Polygon, models.Building.polygon_id == models.Polygon.id)
        .order_by(models.Polygon.name, models.Building.code)
    ).all()
    return [
        schemas.BuildingWithPolygonOut(
            **schemas.BuildingOut.model_validate(b).model_dump(), polygon_name=p
        )
        for b, p in rows
    ]


@router.get("/api/buildings/thresholds/defaults")
def get_default_thresholds():
    """Valores globales usados cuando una nave no tiene umbrales propios."""
    return {
        "temp_warning": anomaly_rules.TEMPERATURE_WARNING,
        "temp_critical": anomaly_rules.TEMPERATURE_CRITICAL,
        "vibration_warning": anomaly_rules.VIBRATION_WARNING,
        "vibration_critical": anomaly_rules.VIBRATION_CRITICAL,
        "humidity_warning": anomaly_rules.HUMIDITY_WARNING,
        "humidity_critical": anomaly_rules.HUMIDITY_CRITICAL,
        "energy_anomaly_warning_pct": anomaly_rules.ENERGY_ANOMALY_WARNING_PCT,
        "energy_anomaly_critical_pct": anomaly_rules.ENERGY_ANOMALY_CRITICAL_PCT,
    }


@router.get("/api/buildings/{building_id}", response_model=schemas.BuildingOut)
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    return building


@router.patch(
    "/api/buildings/{building_id}/thresholds",
    response_model=schemas.BuildingOut,
    dependencies=[Depends(require_admin)],
)
def update_building_thresholds(
    building_id: int, payload: schemas.BuildingThresholdsUpdate, db: Session = Depends(get_db)
):
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    for field, value in payload.model_dump().items():
        setattr(building, field, value)
    db.commit()
    db.refresh(building)
    return building


def _vibration_trend_pct(db: Session, building_id: int, now: datetime) -> float | None:
    """% de cambio de la vibracion media de las ultimas 24h frente a los 7
    dias anteriores. Una tendencia al alza puede anticipar un fallo mecanico."""
    vibration_ids = db.execute(
        select(models.Sensor.id).where(
            models.Sensor.building_id == building_id,
            models.Sensor.sensor_type == models.SensorType.vibration,
        )
    ).scalars().all()
    if not vibration_ids:
        return None

    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    recent_avg = db.execute(
        select(func.avg(models.SensorReading.value)).where(
            models.SensorReading.sensor_id.in_(vibration_ids),
            models.SensorReading.timestamp >= since_24h,
        )
    ).scalar_one()
    baseline_avg = db.execute(
        select(func.avg(models.SensorReading.value)).where(
            models.SensorReading.sensor_id.in_(vibration_ids),
            models.SensorReading.timestamp >= since_7d,
            models.SensorReading.timestamp < since_24h,
        )
    ).scalar_one()

    if recent_avg is None or baseline_avg is None or baseline_avg <= 0:
        return None
    return round((recent_avg - baseline_avg) / baseline_avg * 100, 1)


@router.get(
    "/api/buildings/{building_id}/dashboard", response_model=schemas.BuildingDashboardOut
)
def building_dashboard(
    building_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")

    sensors = db.execute(
        select(models.Sensor).where(models.Sensor.building_id == building_id)
    ).scalars().all()
    sensors_out = [_sensor_latest(db, s) for s in sensors]

    active_alerts = db.execute(
        select(models.Alert)
        .where(
            models.Alert.building_id == building_id,
            models.Alert.status == models.AlertStatus.active,
        )
        .order_by(models.Alert.created_at.desc())
    ).scalars().all()

    incidents = db.execute(
        select(models.Incident)
        .where(models.Incident.building_id == building_id)
        .order_by(models.Incident.created_at.desc())
        .limit(20)
    ).scalars().all()

    polygon_buildings = db.execute(
        select(models.Building).where(models.Building.polygon_id == building.polygon_id)
    ).scalars().all()
    totals = energy_totals_24h(db, polygon_buildings)
    efficiency_values = {
        b.id: kwh_per_m2(totals[b.id], b.area_m2) for b in polygon_buildings
    }
    scores = efficiency_scores(efficiency_values)
    valid_values = [v for v in efficiency_values.values() if v is not None]
    polygon_avg = round(sum(valid_values) / len(valid_values), 3) if valid_values else None

    now = datetime.now(UTC)
    energy_sensor_ids = [s.id for s in sensors if s.sensor_type == models.SensorType.energy]
    predicted_total, _ = predict_energy(db, energy_sensor_ids, now)

    since_7d = now - timedelta(days=7)
    alert_count_7d = db.execute(
        select(func.count(models.Alert.id)).where(
            models.Alert.building_id == building_id,
            models.Alert.created_at >= since_7d,
        )
    ).scalar_one()
    vibration_trend_pct = _vibration_trend_pct(db, building_id, now)
    risk_score = maintenance_risk_score(alert_count_7d, vibration_trend_pct, building.status.value)

    return schemas.BuildingDashboardOut(
        building=building,
        sensors=sensors_out,
        active_alerts=active_alerts,
        incidents=incidents,
        efficiency_kwh_per_m2=(
            round(efficiency_values[building.id], 3)
            if efficiency_values[building.id] is not None
            else None
        ),
        efficiency_score=scores[building.id],
        polygon_avg_kwh_per_m2=polygon_avg,
        predicted_energy_kwh_24h=predicted_total,
        maintenance_risk_score=risk_score,
        maintenance_risk_label=risk_label(risk_score),
    )
