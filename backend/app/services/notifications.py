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
from datetime import UTC, datetime
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Alert, Building, Polygon, User, UserRole

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


def _send(
    subject: str,
    body: str,
    recipients: list[str],
    attachment: tuple[str, bytes, str] | None = None,
) -> None:
    """attachment: (nombre_fichero, contenido, subtipo_mime) p.ej.
    ("informe.pdf", pdf_bytes, "pdf")."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    if attachment:
        filename, content, subtype = attachment
        maintype = "application"
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

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


def _staff_recipients(db: Session) -> list[str]:
    """Admins y operarios (viewers): son quienes ven el poligono completo y
    a quienes tiene sentido mandarles un informe agregado. Los tenants no
    entran aqui: solo ven su propia nave y no tienen acceso al endpoint de
    informes (ver app/routers/reports.py)."""
    staff = db.execute(
        select(User.email).where(User.role.in_([UserRole.admin, UserRole.viewer]))
    ).scalars().all()
    return sorted(set(staff))


def notify_scheduled_report(
    db: Session, polygon: Polygon, period: str, pdf_bytes: bytes
) -> bool:
    """Manda el informe periodico (PDF) por email a admins/operarios.
    Devuelve True si se mando, False si SMTP no esta configurado o no hay
    destinatarios (en ambos casos no es un error, solo no hay nada que
    hacer)."""
    if not is_email_configured():
        return False

    recipients = _staff_recipients(db)
    if not recipients:
        return False

    period_label = {"weekly": "semanal", "monthly": "mensual"}.get(period, period)
    link = f"{settings.app_base_url}/polygon/{polygon.id}"
    subject = f"[INDU-TWIN] Informe {period_label} — {polygon.name}"
    body = (
        f"Adjunto el informe {period_label} de {polygon.name}.\n\n"
        f"Ver el panel en vivo: {link}\n"
    )
    date_tag = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"informe_{polygon.name.lower().replace(' ', '_')}_{period}_{date_tag}.pdf"

    try:
        _send(subject, body, recipients, attachment=(filename, pdf_bytes, "pdf"))
        return True
    except Exception:
        logger.exception(
            "No se pudo enviar el informe automatico (polygon_id=%s, period=%s)",
            polygon.id,
            period,
        )
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
