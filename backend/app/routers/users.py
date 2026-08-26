from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, require_admin
from app.security import hash_password
from app.services.plans import check_limit, current_limits, current_plan_name

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(models.User).order_by(models.User.created_at)).scalars().all()


@router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Ya existe un usuario con ese email")

    used = db.execute(select(func.count(models.User.id))).scalar_one()
    check_limit(used, current_limits().max_users, "usuarios", current_plan_name())

    building_id = payload.building_id
    if payload.role == models.UserRole.tenant:
        if not building_id:
            raise HTTPException(400, "Una cuenta de empresa necesita una nave asignada")
        if not db.get(models.Building, building_id):
            raise HTTPException(404, "Nave no encontrada")
    else:
        building_id = None

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        building_id=building_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.id == admin.id and payload.role is not None and payload.role != models.UserRole.admin:
        raise HTTPException(400, "No puedes quitarte a ti mismo el rol de administrador")

    data = payload.model_dump(exclude_unset=True)
    new_role = data.get("role", user.role)
    new_building_id = data.get("building_id", user.building_id)
    if new_role == models.UserRole.tenant:
        if not new_building_id:
            raise HTTPException(400, "Una cuenta de empresa necesita una nave asignada")
        if not db.get(models.Building, new_building_id):
            raise HTTPException(404, "Nave no encontrada")
    else:
        new_building_id = None

    for field, value in data.items():
        setattr(user, field, value)
    user.building_id = new_building_id
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(user)
    db.commit()
