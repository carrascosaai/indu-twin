from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import forbid_tenant, get_current_user, get_db, require_admin
from app.services.plans import check_limit, current_limits, current_plan_name

router = APIRouter(
    prefix="/api/polygons", tags=["polygons"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.PolygonOut], dependencies=[Depends(forbid_tenant)])
def list_polygons(db: Session = Depends(get_db)):
    return db.execute(select(models.Polygon)).scalars().all()


@router.post(
    "", response_model=schemas.PolygonOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_polygon(payload: schemas.PolygonCreate, db: Session = Depends(get_db)):
    used = db.execute(select(func.count(models.Polygon.id))).scalar_one()
    check_limit(used, current_limits().max_polygons, "polígonos", current_plan_name())

    polygon = models.Polygon(**payload.model_dump())
    db.add(polygon)
    db.commit()
    db.refresh(polygon)
    return polygon


@router.get(
    "/{polygon_id}", response_model=schemas.PolygonOut, dependencies=[Depends(forbid_tenant)]
)
def get_polygon(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    return polygon


@router.delete("/{polygon_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_polygon(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    db.delete(polygon)
    db.commit()
