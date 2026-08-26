from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import check_building_access, get_current_user, get_db, require_admin
from app.models import generate_sensor_api_key

router = APIRouter(tags=["sensors"], dependencies=[Depends(get_current_user)])


@router.get("/api/buildings/{building_id}/sensors", response_model=list[schemas.SensorOut])
def list_sensors(
    building_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    return db.execute(
        select(models.Sensor).where(models.Sensor.building_id == building_id)
    ).scalars().all()


@router.get(
    "/api/sensors/{sensor_id}/readings", response_model=list[schemas.SensorReadingOut]
)
def get_sensor_readings(
    sensor_id: int,
    hours: int = Query(24, ge=1, le=24 * 30),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    sensor = db.get(models.Sensor, sensor_id)
    if not sensor:
        raise HTTPException(404, "Sensor no encontrado")
    check_building_access(user, sensor.building_id)
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = db.execute(
        select(models.SensorReading)
        .where(
            models.SensorReading.sensor_id == sensor_id,
            models.SensorReading.timestamp >= since,
        )
        .order_by(models.SensorReading.timestamp.asc())
    ).scalars().all()
    return rows


@router.get(
    "/api/sensors/{sensor_id}/api-key",
    response_model=schemas.SensorApiKeyOut,
    dependencies=[Depends(require_admin)],
)
def get_sensor_api_key(sensor_id: int, db: Session = Depends(get_db)):
    """Clave a programar en el dispositivo fisico para que pueda mandar
    lecturas de este sensor a /api/ingest/reading. Solo para admins."""
    sensor = db.get(models.Sensor, sensor_id)
    if not sensor:
        raise HTTPException(404, "Sensor no encontrado")
    return schemas.SensorApiKeyOut(sensor_id=sensor.id, api_key=sensor.api_key)


@router.post(
    "/api/sensors/{sensor_id}/api-key/regenerate",
    response_model=schemas.SensorApiKeyOut,
    dependencies=[Depends(require_admin)],
)
def regenerate_sensor_api_key(sensor_id: int, db: Session = Depends(get_db)):
    """Invalida la clave actual y genera una nueva: util si se sospecha que
    la clave de un dispositivo se ha filtrado."""
    sensor = db.get(models.Sensor, sensor_id)
    if not sensor:
        raise HTTPException(404, "Sensor no encontrado")
    sensor.api_key = generate_sensor_api_key()
    db.commit()
    return schemas.SensorApiKeyOut(sensor_id=sensor.id, api_key=sensor.api_key)
