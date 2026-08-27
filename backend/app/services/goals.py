"""Objetivos de reduccion de consumo (KPIs) configurables por un admin.

Un objetivo compara el consumo real desde que se creo contra un
"presupuesto" calculado a partir de la linea base capturada al crearlo
(el consumo medio diario de los `baseline_days` anteriores). Se expresa
todo en kWh acumulados dentro de lo que ya ha transcurrido del periodo del
objetivo, para que se pueda leer como una barra de progreso de tipo
"llevas X kWh consumidos de un presupuesto de Y kWh hasta hoy" - mas facil
de entender de un vistazo que un porcentaje abstracto.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas


def _energy_sensor_ids(
    db: Session, polygon_id: int, building_id: int | None
) -> list[int]:
    building_filter = (
        [models.Building.id == building_id]
        if building_id is not None
        else [models.Building.polygon_id == polygon_id]
    )
    return db.execute(
        select(models.Sensor.id)
        .join(models.Building, models.Sensor.building_id == models.Building.id)
        .where(models.Sensor.sensor_type == models.SensorType.energy, *building_filter)
    ).scalars().all()


def _energy_sum(
    db: Session, sensor_ids: list[int], since: datetime, until: datetime | None = None
) -> float:
    if not sensor_ids:
        return 0.0
    conditions = [
        models.SensorReading.sensor_id.in_(sensor_ids),
        models.SensorReading.timestamp >= since,
    ]
    if until is not None:
        conditions.append(models.SensorReading.timestamp < until)
    return db.execute(
        select(func.coalesce(func.sum(models.SensorReading.value), 0.0)).where(*conditions)
    ).scalar_one()


def create_goal(
    db: Session,
    polygon_id: int,
    payload: schemas.EnergyGoalCreate,
    baseline_days: int = 30,
) -> models.EnergyGoal:
    if payload.building_id is not None:
        building = db.get(models.Building, payload.building_id)
        if building is None or building.polygon_id != polygon_id:
            raise ValueError("La nave no pertenece a este poligono")

    now = datetime.now(UTC)
    sensor_ids = _energy_sensor_ids(db, polygon_id, payload.building_id)
    baseline_kwh = _energy_sum(db, sensor_ids, since=now - timedelta(days=baseline_days), until=now)

    goal = models.EnergyGoal(
        polygon_id=polygon_id,
        building_id=payload.building_id,
        title=payload.title,
        target_reduction_pct=payload.target_reduction_pct,
        baseline_kwh=baseline_kwh,
        baseline_days=baseline_days,
        start_date=now,
        end_date=now + timedelta(days=payload.duration_days),
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def goal_progress(db: Session, goal: models.EnergyGoal, now: datetime | None = None) -> schemas.EnergyGoalOut:
    now = now or datetime.now(UTC)
    start_date = goal.start_date if goal.start_date.tzinfo else goal.start_date.replace(tzinfo=UTC)
    end_date = goal.end_date if goal.end_date.tzinfo else goal.end_date.replace(tzinfo=UTC)

    window_end = min(now, end_date)
    elapsed_days = max((window_end - start_date).total_seconds() / 86400, 0.0)

    baseline_daily_avg = goal.baseline_kwh / goal.baseline_days if goal.baseline_days else 0.0
    target_daily_avg = baseline_daily_avg * (1 - goal.target_reduction_pct / 100)

    expected_kwh_at_baseline = baseline_daily_avg * elapsed_days
    target_kwh = target_daily_avg * elapsed_days

    sensor_ids = _energy_sensor_ids(db, goal.polygon_id, goal.building_id)
    current_kwh = _energy_sum(db, sensor_ids, since=start_date, until=window_end) if elapsed_days > 0 else 0.0

    reduction_needed = expected_kwh_at_baseline - target_kwh
    if reduction_needed > 0:
        reduction_achieved = expected_kwh_at_baseline - current_kwh
        progress_pct = max(0.0, min(100.0, reduction_achieved / reduction_needed * 100))
    else:
        # target_reduction_pct <= 0 (objetivo sin reduccion real, raro pero
        # no invalido): se considera cumplido mientras no se supere la linea base.
        progress_pct = 100.0 if current_kwh <= expected_kwh_at_baseline else 0.0

    is_on_track = current_kwh <= target_kwh
    days_remaining = max((end_date - now).days, 0)

    return schemas.EnergyGoalOut(
        id=goal.id,
        polygon_id=goal.polygon_id,
        building_id=goal.building_id,
        title=goal.title,
        target_reduction_pct=goal.target_reduction_pct,
        baseline_kwh=round(goal.baseline_kwh, 2),
        baseline_days=goal.baseline_days,
        start_date=goal.start_date,
        end_date=goal.end_date,
        created_at=goal.created_at,
        current_kwh=round(current_kwh, 2),
        target_kwh=round(target_kwh, 2),
        progress_pct=round(progress_pct, 1),
        is_on_track=is_on_track,
        days_remaining=days_remaining,
    )
