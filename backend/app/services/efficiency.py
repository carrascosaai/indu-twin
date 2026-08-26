"""Indicadores de eficiencia energetica por nave.

Metrica simple y explicable para el MVP: consumo (kWh) de las ultimas 24h
dividido por superficie (m2). Se compara cada nave contra las demas del
mismo poligono para dar una puntuacion 0-100 (100 = la mas eficiente del
grupo). Facil de sustituir mas adelante por un modelo que tenga en cuenta
tipo de nave, ocupacion horaria, etc.
"""


def kwh_per_m2(energy_kwh: float, area_m2: float | None) -> float | None:
    if not area_m2 or area_m2 <= 0:
        return None
    return energy_kwh / area_m2


def efficiency_scores(values: dict[int, float | None]) -> dict[int, int]:
    """Puntua cada nave (0-100, mayor = mas eficiente) relativo al resto del grupo."""
    valid = {k: v for k, v in values.items() if v is not None}
    if not valid:
        return dict.fromkeys(values, 100)

    lo, hi = min(valid.values()), max(valid.values())
    scores: dict[int, int] = {}
    for building_id, value in values.items():
        if value is None or hi == lo:
            scores[building_id] = 100
        else:
            scores[building_id] = round(100 - 100 * (value - lo) / (hi - lo))
    return scores
