from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import check_building_access, forbid_tenant, get_current_user, get_db

router = APIRouter(tags=["incidents"], dependencies=[Depends(get_current_user)])


@router.get(
    "/api/polygons/{polygon_id}/incidents",
    response_model=list[schemas.IncidentOut],
    dependencies=[Depends(forbid_tenant)],
)
def list_polygon_incidents(
    polygon_id: int,
    status: models.IncidentStatus | None = None,
    db: Session = Depends(get_db),
):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    stmt = (
        select(models.Incident)
        .join(models.Building, models.Incident.building_id == models.Building.id)
        .where(models.Building.polygon_id == polygon_id)
    )
    if status is not None:
        stmt = stmt.where(models.Incident.status == status)
    stmt = stmt.order_by(models.Incident.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/api/buildings/{building_id}/incidents", response_model=list[schemas.IncidentOut])
def list_incidents(
    building_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    return db.execute(
        select(models.Incident)
        .where(models.Incident.building_id == building_id)
        .order_by(models.Incident.created_at.desc())
    ).scalars().all()


@router.post(
    "/api/buildings/{building_id}/incidents", response_model=schemas.IncidentOut, status_code=201
)
def create_incident(
    building_id: int,
    payload: schemas.IncidentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_building_access(user, building_id)
    building = db.get(models.Building, building_id)
    if not building:
        raise HTTPException(404, "Nave no encontrada")
    incident = models.Incident(building_id=building_id, **payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/api/incidents/{incident_id}", response_model=schemas.IncidentOut)
def update_incident(
    incident_id: int,
    payload: schemas.IncidentUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    incident = db.get(models.Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incidencia no encontrada")
    check_building_access(user, incident.building_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(incident, field, value)
    if data.get("status") == models.IncidentStatus.resolved and not incident.resolved_at:
        incident.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(incident)
    return incident
