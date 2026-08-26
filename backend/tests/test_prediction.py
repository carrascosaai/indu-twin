from datetime import datetime

from app.services.prediction import MIN_HOURS_WITH_DATA, hourly_profile, predict_next_24h


def test_hourly_profile_averages_per_hour():
    totals = [(8, 4.0), (8, 6.0), (9, 2.0)]
    profile = hourly_profile(totals)
    assert profile[8] == 5.0
    assert profile[9] == 2.0


def test_predict_next_24h_returns_none_with_insufficient_history():
    totals = [(8, 4.0), (9, 2.0)]  # muy pocas horas distintas con datos
    total, series = predict_next_24h(totals, datetime(2026, 1, 1, 12, 0))
    assert total is None
    assert series == []


def test_predict_next_24h_with_enough_history():
    totals = [(h, 2.0) for h in range(MIN_HOURS_WITH_DATA)]
    total, series = predict_next_24h(totals, datetime(2026, 1, 1, 12, 0))
    assert total is not None
    assert len(series) == 24
    # Las horas sin datos se predicen a 0
    assert total == sum(v for _, v in series)


def test_predict_next_24h_series_covers_next_24_hours_in_order():
    totals = [(h, 1.0) for h in range(MIN_HOURS_WITH_DATA)]
    start = datetime(2026, 1, 1, 12, 0)
    _, series = predict_next_24h(totals, start)
    assert series[0][0].hour == 13
    assert len(series) == 24
    timestamps = [ts for ts, _ in series]
    assert timestamps == sorted(timestamps)
