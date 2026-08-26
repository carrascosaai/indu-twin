import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_current_user, get_db
from app.security import (
    create_access_token,
    generate_password_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.services import notifications, rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("indu_twin.auth")

RESET_TOKEN_TTL = timedelta(hours=1)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Clave por IP + email: frena fuerza bruta sin bloquear a otros usuarios
    # detras del mismo NAT/proxy que intentan iniciar sesion con su cuenta.
    key = f"{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    if rate_limit.is_blocked(key):
        raise HTTPException(429, "Demasiados intentos fallidos. Intenta de nuevo en unos minutos.")

    user = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        rate_limit.register_failure(key)
        raise HTTPException(401, "Email o contraseña incorrectos")
    rate_limit.reset(key)
    token = create_access_token(subject=user.email)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.get("/setup-status", response_model=schemas.SetupStatus)
def setup_status(db: Session = Depends(get_db)):
    """Publico: le dice al frontend si esta instancia todavia no tiene
    ningun usuario, para poder ofrecer el alta de la primera cuenta admin
    sin que un operador tenga que crearla a mano en la base de datos."""
    user_count = db.execute(select(func.count(models.User.id))).scalar_one()
    return schemas.SetupStatus(needs_setup=user_count == 0)


@router.post("/register", response_model=schemas.Token, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Crea la primera cuenta admin de una instancia nueva de INDU-TWIN.

    Cada cliente tiene su propio despliegue (su propio contenedor y base de
    datos, ver docker-compose.yml), asi que no hace falta aislar
    organizaciones dentro de una misma base de datos: basta con permitir
    esto una unica vez, mientras no exista ningun usuario todavia. A partir
    de ahi, el resto de cuentas se crean desde /users (solo admins).
    """
    user_count = db.execute(select(func.count(models.User.id))).scalar_one()
    if user_count > 0:
        raise HTTPException(
            403, "Esta instancia ya tiene cuentas. Pide acceso a tu administrador."
        )
    if len(payload.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    existing = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Ya existe un usuario con ese email")

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=models.UserRole.admin,
    )
    db.add(user)
    db.commit()

    token = create_access_token(subject=user.email)
    return schemas.Token(access_token=token)


@router.post("/forgot-password", response_model=schemas.MessageOut)
def forgot_password(
    payload: schemas.ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
):
    """Publico. Siempre responde con el mismo mensaje exista o no la cuenta,
    para no filtrar que emails estan registrados."""
    key = f"reset:{request.client.host if request.client else 'unknown'}:{payload.email.lower()}"
    generic_message = schemas.MessageOut(
        message=(
            "Si existe una cuenta con ese email, te hemos enviado un enlace "
            "para restablecer la contraseña."
        )
    )
    if rate_limit.is_blocked(key):
        return generic_message

    user = db.execute(
        select(models.User).where(models.User.email == payload.email)
    ).scalar_one_or_none()
    if not user:
        rate_limit.register_failure(key)
        return generic_message

    raw_token, token_hash = generate_password_reset_token()
    user.reset_token_hash = token_hash
    user.reset_token_expires_at = datetime.now(UTC) + RESET_TOKEN_TTL
    db.commit()

    sent = notifications.send_password_reset_email(user, raw_token)
    if not sent:
        # SMTP no configurado (desarrollo/demo): se deja constancia del
        # enlace en el log para poder completar el flujo igualmente.
        logger.warning(
            "SMTP no configurado, enlace de recuperacion para %s: "
            "/reset-password?token=%s",
            user.email,
            raw_token,
        )
    rate_limit.register_failure(key)
    return generic_message


@router.post("/reset-password", response_model=schemas.MessageOut)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(payload.new_password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")

    token_hash = hash_reset_token(payload.token)
    user = db.execute(
        select(models.User).where(models.User.reset_token_hash == token_hash)
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    # SQLite no conserva la zona horaria: lo que vuelve de la BD es naive,
    # aunque se guardo un datetime con tzinfo=UTC. Se asume UTC al leerlo.
    expires_at = user.reset_token_expires_at if user else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if not user or not expires_at or expires_at < now:
        raise HTTPException(400, "El enlace no es válido o ha caducado")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.commit()
    return schemas.MessageOut(message="Contraseña actualizada. Ya puedes iniciar sesión.")
