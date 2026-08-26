from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import check_building_access, get_current_user, get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    polygon_id: int | None = None,
    building_id: int | None = None,
    status: models.AlertStatus | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # Una cuenta de empresa solo ve las alertas de su propia nave, sin
    # importar que filtros pida: ignoramos polygon_id y fijamos building_id.
    if user.role == models.UserRole.tenant:
        polygon_id = None
        building_id = user.building_id
        if building_id is None:
            return []

    stmt = select(models.Alert)
    if building_id is not None:
        stmt = stmt.where(models.Alert.building_id == building_id)
    if polygon_id is not None:
        stmt = stmt.join(models.Building).where(models.Building.polygon_id == polygon_id)
    if status is not None:
        stmt = stmt.where(models.Alert.status == status)
    stmt = stmt.order_by(models.Alert.created_at.desc()).limit(limit)
    return db.execute(stmt).scalars().all()


@router.patch("/{alert_id}/resolve", response_model=schemas.AlertOut)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    alert = db.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alerta no encontrada")
    check_building_access(user, alert.building_id)
    alert.status = models.AlertStatus.resolved
    alert.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)

    from app.services.simulator import update_building_status

    building = db.get(models.Building, alert.building_id)
    update_building_status(db, building)
    db.commit()
    return alert
