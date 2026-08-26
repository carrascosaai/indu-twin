"""Mantenimiento predictivo basico: puntuacion de riesgo por reglas.

Combina tres senales sencillas y explicables en una puntuacion 0-100:
  - Cuantas alertas ha tenido la nave en los ultimos 7 dias.
  - Si la vibracion media reciente esta subiendo respecto a su historico
    (una tendencia al alza en vibracion suele preceder a un fallo mecanico).
  - El estado actual de la nave.

No es un modelo entrenado: son reglas con pesos fijos, facil de sustituir
mas adelante por un modelo real (ej. supervivencia/regresion sobre tiempo
hasta el proximo fallo) manteniendo la misma interfaz de salida.
"""

ALERT_WEIGHT = 8
ALERT_CAP = 40
VIBRATION_TREND_WEIGHT = 0.5
VIBRATION_TREND_CAP = 30
STATUS_WEIGHTS = {"critical": 20, "warning": 10, "normal": 0}


def maintenance_risk_score(
    alert_count_7d: int,
    vibration_trend_pct: float | None,
    current_status: str,
) -> int:
    score = min(alert_count_7d * ALERT_WEIGHT, ALERT_CAP)
    if vibration_trend_pct is not None and vibration_trend_pct > 0:
        score += min(vibration_trend_pct * VIBRATION_TREND_WEIGHT, VIBRATION_TREND_CAP)
    score += STATUS_WEIGHTS.get(current_status, 0)
    return min(round(score), 100)


def risk_label(score: int) -> str:
    if score >= 70:
        return "Alto"
    if score >= 35:
        return "Medio"
    return "Bajo"
