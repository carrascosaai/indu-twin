import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db
from app.services.simulator import process_new_reading

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/reading", response_model=schemas.SensorReadingOut, status_code=201)
def ingest_reading(payload: schemas.ReadingIngest, db: Session = Depends(get_db)):
    """Endpoint preparado para sensores ESP32 reales (HTTP POST).

    Deliberadamente NO exige el JWT de usuario: lo llaman dispositivos, no
    navegadores. En su lugar, cada sensor tiene su propia API key (ver
    `Sensor.api_key`) que el dispositivo fisico debe mandar junto a la
    lectura: sin ella cualquiera podria inyectar datos falsos en cualquier
    sensor. Reutiliza la misma logica de reglas/alertas que el simulador via
    `process_new_reading`.
    """
    sensor = db.get(models.Sensor, payload.sensor_id)
    if not sensor:
        raise HTTPException(404, "Sensor no encontrado")
    if not secrets.compare_digest(payload.api_key, sensor.api_key):
        raise HTTPException(401, "API key invalida para este sensor")
    reading = process_new_reading(db, sensor, payload.value, payload.timestamp)
    db.commit()
    db.refresh(reading)
    return reading
