from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def normalize_database_url(url: str) -> str:
    """Render (y otros proveedores) a veces dan la URL de Postgres con el
    esquema heredado "postgres://", que SQLAlchemy 1.4+ ya no acepta
    directamente (hace falta "postgresql://"). Normalizarlo aqui evita tener
    que acordarse de arreglarlo a mano cada vez que se copia la connection
    string desde el panel de Render."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


_database_url = normalize_database_url(settings.database_url)

connect_args = {"check_same_thread": False} if _database_url.startswith("sqlite") else {}
engine = create_engine(_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
