"""Limitador de intentos simple en memoria, pensado para frenar fuerza
bruta contra /api/auth/login. Suficiente para un despliegue de una sola
instancia; si se escala a varios workers/instancias habria que moverlo a
Redis u otro almacen compartido."""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_attempts: dict[str, list[float]] = defaultdict(list)


def _prune(key: str, now: float) -> None:
    _attempts[key] = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]


def is_blocked(key: str) -> bool:
    now = time.time()
    _prune(key, now)
    return len(_attempts[key]) >= MAX_ATTEMPTS


def register_failure(key: str) -> None:
    now = time.time()
    _prune(key, now)
    _attempts[key].append(now)


def reset(key: str) -> None:
    _attempts.pop(key, None)
