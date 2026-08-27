"""Limitador de intentos simple en memoria. Suficiente para un despliegue de
una sola instancia; si se escala a varios workers/instancias habria que
moverlo a Redis u otro almacen compartido.

Dos usos, con semantica distinta a proposito:
  - Login (`is_blocked`/`register_failure`/`reset`): solo cuenta los
    intentos FALLIDOS, para frenar fuerza bruta sin penalizar a nadie que
    acierte la contraseña a la primera.
  - Ingesta de sensores (`hit`): cuenta TODAS las peticiones, acierten o no,
    para frenar un firmware con un bucle sin `delay` o un uso indebido de
    una api_key filtrada - aqui no hay "intento fallido" que perdonar, el
    problema es simplemente demasiado trafico.
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_attempts: dict[str, list[float]] = defaultdict(list)


def _prune(bucket: dict[str, list[float]], key: str, now: float, window_seconds: float) -> None:
    bucket[key] = [t for t in bucket[key] if now - t < window_seconds]


def is_blocked(key: str) -> bool:
    now = time.time()
    _prune(_attempts, key, now, WINDOW_SECONDS)
    return len(_attempts[key]) >= MAX_ATTEMPTS


def register_failure(key: str) -> None:
    now = time.time()
    _prune(_attempts, key, now, WINDOW_SECONDS)
    _attempts[key].append(now)


def reset(key: str) -> None:
    _attempts.pop(key, None)


# ---------- Limitador generico por ventana deslizante (ingesta de sensores) ----------

_hits: dict[str, list[float]] = defaultdict(list)


def hit(key: str, max_hits: int, window_seconds: float) -> bool:
    """Registra una peticion para `key` y devuelve True si con esta ya se ha
    superado el limite (deberia rechazarse). A diferencia de is_blocked, la
    peticion cuenta siempre, tanto si se va a aceptar como si no."""
    now = time.time()
    _prune(_hits, key, now, window_seconds)
    _hits[key].append(now)
    return len(_hits[key]) > max_hits
