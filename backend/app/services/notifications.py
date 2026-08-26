"""Notificaciones por email de alertas criticas.

Un dashboard pasivo no sirve de mucho si nadie lo esta mirando: un gestor
de poligono no va a tener la pantalla abierta todo el dia. Cuando salta una
alerta critica, se manda un email a quien puede actuar (admins/operarios
del poligono, y a la empresa duena de la nave si tiene cuenta tenant).

Si SMTP no esta configurado (SMTP_HOST vacio), esto no hace nada: no rompe
el flujo de ingesta ni la demo sin credenciales de correo.
"""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Alert, Building, User, UserRole

logger = logging.getLogger("indu_twin.notifications")


def is_email_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def _recipients(db: Session, building: Building) -> list[str]:
    staff = db.execute(
        select(User.email).where(User.role.in_([UserRole.admin, UserRole.viewer]))
    ).scalars().all()
    tenant = db.execute(
        select(User.email).where(
            User.role == UserRole.tenant, User.building_id == building.id
        )
    ).scalars().all()
    return sorted(set(staff) | set(tenant))


def _send(subject: str, body: str, recipients: list[str]) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_password_reset_email(user: User, raw_token: str) -> bool:
    """Manda el enlace de recuperacion de contrasena. Devuelve True si se
    mando de verdad; False si SMTP no esta configurado (en ese caso, quien
    llama debe loguear el enlace para poder probarlo en desarrollo)."""
    if not is_email_configured():
        return False

    link = f"{settings.app_base_url}/reset-password?token={raw_token}"
    subject = "[INDU-TWIN] Recupera tu contraseña"
    body = (
        f"Hola {user.full_name},\n\n"
        "Alguien (esperamos que tú) ha pedido restablecer la contraseña de "
        f"esta cuenta ({user.email}).\n\n"
        f"Crea una nueva contraseña aquí: {link}\n\n"
        "El enlace caduca en 1 hora. Si no has sido tú, ignora este mensaje.\n"
    )
    try:
        _send(subject, body, [user.email])
        return True
    except Exception:
        logger.exception("No se pudo enviar el email de recuperacion (user_id=%s)", user.id)
        return False


def notify_critical_alert(db: Session, alert: Alert, building: Building) -> None:
    """Manda el aviso si SMTP esta configurado. Cualquier fallo se registra
    en el log pero nunca interrumpe la ingesta de la lectura que lo origino:
    un problema de correo no puede tumbar el pipeline de sensores."""
    if not is_email_configured():
        return

    recipients = _recipients(db, building)
    if not recipients:
        return

    link = f"{settings.app_base_url}/building/{building.id}"
    subject = f"[INDU-TWIN] Alerta critica en {building.name}"
    body = (
        f"{alert.message}\n\n"
        f"Nave: {building.name} ({building.code})\n"
        f"Ver en el panel: {link}\n"
    )
    try:
        _send(subject, body, recipients)
    except Exception:
        logger.exception("No se pudo enviar el email de alerta critica (alert_id=%s)", alert.id)
