import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db
from app.services import rate_limit
from app.services.simulator import process_new_reading

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# Un sensor real manda como mucho una lectura por minuto (ver
# SEND_INTERVAL_MS en el firmware); esto deja mucho margen por encima de eso
# y solo frena un uso claramente anormal - un firmware con un bucle sin
# `delay`, o una api_key filtrada y usada para inundar el endpoint.
INGEST_MAX_REQUESTS = 30
INGEST_WINDOW_SECONDS = 60


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
    if rate_limit.hit(
        f"ingest:{payload.sensor_id}", INGEST_MAX_REQUESTS, INGEST_WINDOW_SECONDS
    ):
        raise HTTPException(429, "Demasiadas lecturas de este sensor en poco tiempo")

    sensor = db.get(models.Sensor, payload.sensor_id)
    if not sensor:
        raise HTTPException(404, "Sensor no encontrado")
    if not secrets.compare_digest(payload.api_key, sensor.api_key):
        raise HTTPException(401, "API key invalida para este sensor")
    if sensor.is_simulated:
        # Primera lectura real de este sensor: el simulador deja de
        # generarle datos de mentira a partir de ahora (ver run_simulation_tick).
        sensor.is_simulated = False
    reading = process_new_reading(db, sensor, payload.value, payload.timestamp)
    db.commit()
    db.refresh(reading)
    return reading
