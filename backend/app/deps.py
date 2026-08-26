from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, UserRole
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    email = decode_access_token(token)
    if not email:
        raise unauthorized
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere rol de administrador")
    return user


def forbid_tenant(user: User = Depends(get_current_user)) -> User:
    """Para endpoints a nivel de poligono (mapa, ranking, exportacion global...)
    que una cuenta de empresa individual (tenant) no debe poder ver."""
    if user.role == UserRole.tenant:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No disponible para cuentas de empresa")
    return user


def check_building_access(user: User, building_id: int) -> None:
    """Una cuenta tenant solo puede acceder a los datos de su propia nave."""
    if user.role == UserRole.tenant and user.building_id != building_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta nave")
