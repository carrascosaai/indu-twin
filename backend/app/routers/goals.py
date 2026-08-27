from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import forbid_tenant, get_current_user, get_db, require_admin
from app.services.goals import create_goal, goal_progress

router = APIRouter(
    tags=["goals"],
    dependencies=[Depends(get_current_user), Depends(forbid_tenant)],
)


@router.get("/api/polygons/{polygon_id}/goals", response_model=list[schemas.EnergyGoalOut])
def list_goals(polygon_id: int, db: Session = Depends(get_db)):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    goals = db.execute(
        select(models.EnergyGoal)
        .where(models.EnergyGoal.polygon_id == polygon_id)
        .order_by(models.EnergyGoal.created_at.desc())
    ).scalars().all()
    return [goal_progress(db, g) for g in goals]


@router.post(
    "/api/polygons/{polygon_id}/goals",
    response_model=schemas.EnergyGoalOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_polygon_goal(
    polygon_id: int, payload: schemas.EnergyGoalCreate, db: Session = Depends(get_db)
):
    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")
    if payload.target_reduction_pct <= 0 or payload.target_reduction_pct >= 100:
        raise HTTPException(400, "El objetivo de reduccion debe estar entre 0 y 100%")
    if payload.duration_days <= 0:
        raise HTTPException(400, "La duracion debe ser mayor que 0 dias")
    try:
        goal = create_goal(db, polygon_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return goal_progress(db, goal)


@router.delete(
    "/api/goals/{goal_id}", status_code=204, dependencies=[Depends(require_admin)]
)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.get(models.EnergyGoal, goal_id)
    if not goal:
        raise HTTPException(404, "Objetivo no encontrado")
    db.delete(goal)
    db.commit()
