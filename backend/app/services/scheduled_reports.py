"""Envio automatico de informes por email (semanal/mensual), sin que nadie
tenga que entrar a la app a descargarlos.

En vez de anclar el envio a un dia de la semana concreto (p.ej. "todos los
lunes"), se guarda cuando se mando el ultimo informe de cada poligono/periodo
en la base de datos (tabla `report_schedules`) y se manda el siguiente en
cuanto ha pasado el intervalo correspondiente. Esto es deliberado: el
servicio corre en el plan free de Render, que duerme el proceso tras un rato
sin trafico y lo despierta con la siguiente peticion HTTP - anclarlo a un
dia/hora concretos se rompe si el proceso esta dormido justo en ese momento.
Con el enfoque de "ha pasado X dias desde el ultimo envio", el informe se
manda igualmente en cuanto el servicio se despierta, aunque sea tarde.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.services import notifications
from app.services.reports import build_report_data, render_pdf

logger = logging.getLogger("indu_twin.scheduled_reports")

CHECK_INTERVAL_SECONDS = 60 * 60  # comprobar cada hora si toca mandar algo

# period -> (nombre para build_report_data, dias minimos entre envios)
_PERIODS: dict[str, tuple[str, int]] = {
    "weekly": ("weekly", 7),
    "monthly": ("monthly", 30),
}


def _due_polygons(db: Session, period: str, min_days: int, now: datetime) -> list[models.Polygon]:
    polygons = db.execute(select(models.Polygon)).scalars().all()
    if not polygons:
        return []

    schedules = {
        s.polygon_id: s
        for s in db.execute(
            select(models.ReportSchedule).where(models.ReportSchedule.period == period)
        ).scalars().all()
    }

    due = []
    for polygon in polygons:
        schedule = schedules.get(polygon.id)
        if schedule is None or schedule.last_sent_at is None:
            due.append(polygon)
        else:
            last_sent = schedule.last_sent_at
            # SQLite no conserva el tzinfo al leer de vuelta un DateTime
            # aunque la columna sea timezone=True (a diferencia de
            # Postgres) - se asume UTC para poder restar sin que Python se
            # queje de mezclar aware/naive.
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=UTC)
            if now - last_sent >= timedelta(days=min_days):
                due.append(polygon)
    return due


def _mark_sent(db: Session, polygon_id: int, period: str, now: datetime) -> None:
    schedule = db.execute(
        select(models.ReportSchedule).where(
            models.ReportSchedule.polygon_id == polygon_id,
            models.ReportSchedule.period == period,
        )
    ).scalar_one_or_none()
    if schedule is None:
        schedule = models.ReportSchedule(polygon_id=polygon_id, period=period)
        db.add(schedule)
    schedule.last_sent_at = now
    db.commit()


def check_and_send_due_reports(db: Session, now: datetime | None = None) -> int:
    """Manda todos los informes que tocan ahora mismo. Devuelve cuantos se
    han mandado de verdad (no cuenta los omitidos por falta de SMTP o de
    destinatarios, ver notify_scheduled_report)."""
    now = now or datetime.now(UTC)
    if not notifications.is_email_configured():
        return 0

    sent = 0
    for period, (report_period_name, min_days) in _PERIODS.items():
        for polygon in _due_polygons(db, period, min_days, now):
            try:
                report = build_report_data(db, polygon, report_period_name)
                pdf_bytes = render_pdf(report)
                if notifications.notify_scheduled_report(db, polygon, period, pdf_bytes):
                    sent += 1
            except Exception:
                logger.exception(
                    "Fallo generando/enviando el informe %s de polygon_id=%s",
                    period,
                    polygon.id,
                )
            # Se marca como enviado tanto si tuvo exito como si fallo por un
            # problema de SMTP puntual: evita reintentar en bucle cada hora
            # y machacar el mismo error. Un fallo real de SMTP se ve en los
            # logs (notify_scheduled_report ya lo registra).
            _mark_sent(db, polygon.id, period, now)

    return sent


async def scheduled_reports_loop() -> None:
    logger.info(
        "Envio automatico de informes activado (comprobando cada %sh)",
        CHECK_INTERVAL_SECONDS // 3600,
    )
    while True:
        try:
            db = SessionLocal()
            try:
                sent = await asyncio.to_thread(check_and_send_due_reports, db)
                if sent:
                    logger.info("Informes automaticos enviados: %d", sent)
            finally:
                db.close()
        except Exception:
            logger.exception("Error en el ciclo de informes automaticos")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
