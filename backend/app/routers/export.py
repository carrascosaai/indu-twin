import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.deps import check_building_access, forbid_tenant, get_current_user, get_db

router = APIRouter(prefix="/api", tags=["export"], dependencies=[Depends(get_current_user)])


def _csv_response(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/polygons/{polygon_id}/export/alerts.csv", dependencies=[Depends(forbid_tenant)])
def export_polygon_alerts(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")

    rows = db.execute(
        select(models.Alert, models.Building.name)
        .join(models.Building, models.Alert.building_id == models.Building.id)
        .where(models.Building.polygon_id == polygon_id)
        .order_by(models.Alert.created_at.desc())
    ).all()

    data = [
        [
            a.id,
            building_name,
            a.severity.value,
            a.alert_type.value,
            a.message,
            a.value,
            a.threshold,
            a.status.value,
            a.created_at.isoformat(),
            a.resolved_at.isoformat() if a.resolved_at else "",
        ]
        for a, building_name in rows
    ]
    header = [
        "id",
        "nave",
        "severidad",
        "tipo",
        "mensaje",
        "valor",
        "umbral",
        "estado",
        "creada",
        "resuelta",
    ]
    return _csv_response(data, header, f"alertas_poligono_{polygon_id}.csv")


@router.get("/buildings/{building_id}/export/readings.csv")
def export_building_readings(
    building_id: int,
    hours: int = Query(24, ge=1, le=24 * 90),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")

    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = db.execute(
        select(models.SensorReading, models.Sensor.sensor_type, models.Sensor.unit)
        .join(models.Sensor, models.SensorReading.sensor_id == models.Sensor.id)
        .where(models.Sensor.building_id == building_id, models.SensorReading.timestamp >= since)
        .order_by(models.SensorReading.timestamp.asc())
    ).all()

    data = [
        [reading.sensor_id, sensor_type.value, reading.value, unit, reading.timestamp.isoformat()]
        for reading, sensor_type, unit in rows
    ]
    header = ["sensor_id", "tipo", "valor", "unidad", "timestamp"]
    return _csv_response(data, header, f"lecturas_nave_{building_id}.csv")
