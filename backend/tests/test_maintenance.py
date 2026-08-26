from app.services.maintenance import maintenance_risk_score, risk_label


def test_no_signals_means_low_risk():
    score = maintenance_risk_score(
        alert_count_7d=0, vibration_trend_pct=None, current_status="normal"
    )
    assert score == 0
    assert risk_label(score) == "Bajo"


def test_alerts_increase_risk_but_are_capped():
    score = maintenance_risk_score(
        alert_count_7d=20, vibration_trend_pct=None, current_status="normal"
    )
    assert score == 40  # tope de alertas


def test_negative_vibration_trend_does_not_increase_risk():
    score = maintenance_risk_score(
        alert_count_7d=0, vibration_trend_pct=-50.0, current_status="normal"
    )
    assert score == 0


def test_rising_vibration_trend_increases_risk_up_to_cap():
    score = maintenance_risk_score(
        alert_count_7d=0, vibration_trend_pct=1000.0, current_status="normal"
    )
    assert score == 30  # tope de tendencia de vibracion


def test_critical_status_adds_risk():
    score = maintenance_risk_score(
        alert_count_7d=0, vibration_trend_pct=None, current_status="critical"
    )
    assert score == 20


def test_combined_signals_can_reach_high_risk():
    score = maintenance_risk_score(
        alert_count_7d=6, vibration_trend_pct=40.0, current_status="critical"
    )
    assert score >= 70
    assert risk_label(score) == "Alto"


def test_score_is_bounded_by_the_sum_of_all_caps():
    # 40 (alertas) + 30 (tendencia vibracion) + 20 (critico) = 90 como maximo teorico
    score = maintenance_risk_score(
        alert_count_7d=100, vibration_trend_pct=5000.0, current_status="critical"
    )
    assert score == 90
    assert score <= 100
