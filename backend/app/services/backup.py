"""Copias de seguridad automaticas de la base de datos SQLite.

Sin esto, si se corrompe el fichero `.db` (disco lleno, contenedor matado a
mitad de escritura, error humano...) se pierden todos los datos del
cliente sin posibilidad de recuperacion. Usa el API `sqlite3.Connection.backup`,
que es seguro incluso con la base de datos abierta y en uso (a diferencia de
copiar el fichero a pelo, que puede capturar una escritura a medias).

Solo aplica cuando `DATABASE_URL` apunta a SQLite; con otros motores (p.ej.
Postgres en produccion) esto no hace nada, y las copias de seguridad se
gestionarian con las herramientas propias del motor (pg_dump, snapshots
gestionados, etc.).
"""

import asyncio
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings

logger = logging.getLogger("indu_twin.backup")

BACKUP_INTERVAL_SECONDS = 24 * 60 * 60
BACKUP_RETENTION = 14


def _sqlite_path() -> Path | None:
    match = re.match(r"sqlite:///(.*)", settings.database_url)
    if not match:
        return None
    return Path(match.group(1)).resolve()


def _backup_dir() -> Path | None:
    db_path = _sqlite_path()
    if db_path is None:
        return None
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _prune_old_backups(backup_dir: Path) -> None:
    backups = sorted(backup_dir.glob("indu_twin_*.db"))
    excess = len(backups) - BACKUP_RETENTION
    for old in backups[: max(excess, 0)]:
        old.unlink(missing_ok=True)


def create_backup() -> Path | None:
    """Crea una copia y aplica la retencion. Devuelve None si no aplica
    (motor distinto de SQLite o base de datos todavia inexistente)."""
    db_path = _sqlite_path()
    if db_path is None or not db_path.exists():
        return None
    backup_dir = _backup_dir()
    if backup_dir is None:
        return None

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"indu_twin_{timestamp}.db"

    src_conn = sqlite3.connect(str(db_path))
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    _prune_old_backups(backup_dir)
    return dest


async def backup_loop() -> None:
    logger.info(
        "Backups automaticos activados (cada %sh, se conservan %d copias)",
        BACKUP_INTERVAL_SECONDS // 3600,
        BACKUP_RETENTION,
    )
    while True:
        try:
            path = await asyncio.to_thread(create_backup)
            if path:
                logger.info("Backup creado: %s", path)
        except Exception:
            logger.exception("Error creando el backup automatico")
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
