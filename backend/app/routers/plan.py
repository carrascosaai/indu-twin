from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_current_user, get_db
from app.services.plans import current_limits, current_plan_name

router = APIRouter(prefix="/api/plan", tags=["plan"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=schemas.PlanStatusOut)
def get_plan_status(db: Session = Depends(get_db)):
    limits = current_limits()
    polygons_used = db.execute(select(func.count(models.Polygon.id))).scalar_one()
    buildings_used = db.execute(select(func.count(models.Building.id))).scalar_one()
    users_used = db.execute(select(func.count(models.User.id))).scalar_one()

    return schemas.PlanStatusOut(
        plan=current_plan_name(),
        polygons=schemas.PlanUsage(used=polygons_used, limit=limits.max_polygons),
        buildings=schemas.PlanUsage(used=buildings_used, limit=limits.max_buildings),
        users=schemas.PlanUsage(used=users_used, limit=limits.max_users),
    )
