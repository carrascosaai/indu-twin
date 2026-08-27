from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.config import settings
from app.models import ReportSchedule
from app.services import scheduled_reports


def _configure_smtp(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr(settings, "smtp_from", "reports@indutwin.test")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")


def test_noop_when_smtp_not_configured(db_session, polygon):
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        sent = scheduled_reports.check_and_send_due_reports(db_session)
        mock_smtp.assert_not_called()
    assert sent == 0


def test_sends_report_when_never_sent_before(monkeypatch, db_session, admin_user, polygon, building):
    _configure_smtp(monkeypatch)
    mock_conn = MagicMock()
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_conn
        sent = scheduled_reports.check_and_send_due_reports(db_session)

    # Un poligono nuevo debe a la vez el semanal y el mensual la primera vez.
    assert sent == 2
    assert mock_conn.send_message.call_count == 2


def test_does_not_resend_before_the_interval_elapses(
    monkeypatch, db_session, admin_user, polygon, building
):
    _configure_smtp(monkeypatch)
    now = datetime.now(UTC)
    db_session.add(ReportSchedule(polygon_id=polygon.id, period="weekly", last_sent_at=now))
    db_session.add(
        ReportSchedule(
            polygon_id=polygon.id, period="monthly", last_sent_at=now - timedelta(days=29)
        )
    )
    db_session.commit()

    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        sent = scheduled_reports.check_and_send_due_reports(db_session, now=now)
        mock_smtp.assert_not_called()
    assert sent == 0


def test_resends_after_interval_elapses(monkeypatch, db_session, admin_user, polygon, building):
    _configure_smtp(monkeypatch)
    now = datetime.now(UTC)
    db_session.add(
        ReportSchedule(
            polygon_id=polygon.id, period="weekly", last_sent_at=now - timedelta(days=8)
        )
    )
    db_session.commit()

    mock_conn = MagicMock()
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_conn
        sent = scheduled_reports.check_and_send_due_reports(db_session, now=now)

    # Semanal toca de nuevo; mensual toca por primera vez (nunca se mando).
    assert sent == 2


def test_marks_schedule_sent_even_if_smtp_fails(monkeypatch, db_session, admin_user, polygon, building):
    _configure_smtp(monkeypatch)
    now = datetime.now(UTC)
    with patch("app.services.notifications.smtplib.SMTP", side_effect=OSError("boom")):
        scheduled_reports.check_and_send_due_reports(db_session, now=now)

    schedules = db_session.query(ReportSchedule).filter_by(polygon_id=polygon.id).all()
    assert len(schedules) == 2
    assert all(s.last_sent_at is not None for s in schedules)
