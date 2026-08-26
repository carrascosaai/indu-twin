"""Limites por plan comercial.

Cada cliente tiene su propio despliegue (ver docker-compose.yml), asi que el
plan es una propiedad de la instancia entera (variable de entorno PLAN), no
de un usuario u organizacion. `None` en un limite significa "sin limite".
"""

from dataclasses import dataclass

from fastapi import HTTPException

from app.config import settings


@dataclass(frozen=True)
class PlanLimits:
    max_polygons: int | None
    max_buildings: int | None
    max_users: int | None


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(max_polygons=1, max_buildings=3, max_users=2),
    "pro": PlanLimits(max_polygons=3, max_buildings=15, max_users=10),
    "business": PlanLimits(max_polygons=None, max_buildings=None, max_users=None),
}


def current_plan_name() -> str:
    plan = settings.plan.strip().lower()
    return plan if plan in PLAN_LIMITS else "free"


def current_limits() -> PlanLimits:
    return PLAN_LIMITS[current_plan_name()]


def check_limit(used: int, limit: int | None, resource_label: str, plan_label: str) -> None:
    """Lanza HTTPException 402 si `used` ya alcanzo el limite del plan."""
    if limit is not None and used >= limit:
        raise HTTPException(
            402,
            f"Has alcanzado el límite de {resource_label} de tu plan "
            f"{plan_label.upper()} ({used}/{limit}). Actualiza de plan para añadir más.",
        )
