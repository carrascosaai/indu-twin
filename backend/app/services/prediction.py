"""Prediccion de consumo energetico, sin ML: perfil horario promedio.

Para cada hora del dia (0-23) se promedia el consumo real de esa hora a lo
largo del historico disponible (varios dias), y se usa ese promedio como
prediccion de esa misma hora para el proximo dia. Es el enfoque clasico
"seasonal naive" para series con patron diario marcado, como el consumo
industrial. Facil de sustituir mas adelante por un modelo entrenado,
manteniendo la misma interfaz (una lista de totales horarios con su hora
del dia como entrada, una prediccion por hora como salida).
"""

from collections import defaultdict
from datetime import datetime, timedelta

MIN_HOURS_WITH_DATA = 8  # por debajo de esto, la prediccion no es fiable


def hourly_profile(hourly_totals: list[tuple[int, float]]) -> dict[int, float]:
    """hourly_totals: lista de (hora_del_dia, total_kwh_de_esa_hora_en_un_dia_concreto).
    Devuelve el promedio de consumo por hora del dia, para las horas con datos."""
    buckets: dict[int, list[float]] = defaultdict(list)
    for hour, total in hourly_totals:
        buckets[hour].append(total)
    return {hour: sum(values) / len(values) for hour, values in buckets.items()}


def predict_next_24h(
    hourly_totals: list[tuple[int, float]], start: datetime
) -> tuple[float | None, list[tuple[datetime, float]]]:
    """Devuelve (total previsto, serie de 24 puntos horarios) a partir de `start`.

    Si no hay suficiente historico, devuelve (None, [])."""
    profile = hourly_profile(hourly_totals)
    if len(profile) < MIN_HOURS_WITH_DATA:
        return None, []

    series: list[tuple[datetime, float]] = []
    total = 0.0
    for i in range(24):
        ts = start + timedelta(hours=i + 1)
        value = round(profile.get(ts.hour, 0.0), 3)
        series.append((ts, value))
        total += value

    return round(total, 2), series
