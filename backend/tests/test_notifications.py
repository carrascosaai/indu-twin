from unittest.mock import MagicMock, patch

from app.config import settings
from app.services import notifications


def _configure_smtp(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr(settings, "smtp_from", "alerts@indutwin.test")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")


def test_is_email_configured_false_by_default():
    assert notifications.is_email_configured() is False


def test_notify_critical_alert_noop_when_not_configured(db_session, building, temperature_sensor):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="test",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        notifications.notify_critical_alert(db_session, alert, building)
        mock_smtp.assert_not_called()


def test_notify_critical_alert_sends_when_configured(
    monkeypatch, db_session, admin_user, building, temperature_sensor
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    _configure_smtp(monkeypatch)
    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="Temperatura critica",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    mock_conn = MagicMock()
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_conn
        notifications.notify_critical_alert(db_session, alert, building)

    mock_conn.send_message.assert_called_once()
    sent_msg = mock_conn.send_message.call_args[0][0]
    assert admin_user.email in sent_msg["To"]


def test_notify_critical_alert_never_raises_on_smtp_failure(
    monkeypatch, db_session, admin_user, building, temperature_sensor
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    _configure_smtp(monkeypatch)
    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="test",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    with patch("app.services.notifications.smtplib.SMTP", side_effect=OSError("boom")):
        notifications.notify_critical_alert(db_session, alert, building)  # no debe lanzar


def test_recipients_include_tenant_of_the_building(
    db_session, admin_user, tenant_user, building
):
    recipients = notifications._recipients(db_session, building)
    assert admin_user.email in recipients
    assert tenant_user.email in recipients


def test_critical_ingest_triggers_notification_when_configured(
    monkeypatch, client, admin_headers, admin_user, temperature_sensor
):
    _configure_smtp(monkeypatch)
    mock_conn = MagicMock()
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_conn
        resp = client.post(
            "/api/ingest/reading",
            json={
                "sensor_id": temperature_sensor.id,
                "api_key": temperature_sensor.api_key,
                "value": 40.0,
            },
        )
    assert resp.status_code == 201
    mock_conn.send_message.assert_called_once()


def test_warning_ingest_does_not_trigger_notification(
    monkeypatch, client, admin_user, temperature_sensor
):
    _configure_smtp(monkeypatch)
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        resp = client.post(
            "/api/ingest/reading",
            json={
                "sensor_id": temperature_sensor.id,
                "api_key": temperature_sensor.api_key,
                "value": 31.0,
            },
        )
        assert resp.status_code == 201
        mock_smtp.assert_not_called()


def _configure_telegram(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", "12345:test-token")


def test_is_telegram_configured_false_by_default():
    assert notifications.is_telegram_configured() is False


def test_notify_critical_alert_sends_telegram_when_configured(
    monkeypatch, db_session, admin_user, building, temperature_sensor
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    _configure_telegram(monkeypatch)
    admin_user.telegram_chat_id = "999888777"
    db_session.commit()

    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="Temperatura critica",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response
    with patch("app.services.notifications.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        notifications.notify_critical_alert(db_session, alert, building)

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert "999888777" in request.data.decode()


def test_notify_critical_alert_skips_users_without_telegram_linked(
    monkeypatch, db_session, admin_user, building, temperature_sensor
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    _configure_telegram(monkeypatch)
    # admin_user.telegram_chat_id sigue siendo None (no lo ha vinculado).
    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="test",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    with patch("app.services.notifications.urllib.request.urlopen") as mock_urlopen:
        notifications.notify_critical_alert(db_session, alert, building)
    mock_urlopen.assert_not_called()


def test_telegram_failure_does_not_block_email(
    monkeypatch, db_session, admin_user, building, temperature_sensor
):
    from app.models import Alert, AlertSeverity, AlertStatus, AlertType

    _configure_smtp(monkeypatch)
    _configure_telegram(monkeypatch)
    admin_user.telegram_chat_id = "999888777"
    db_session.commit()

    alert = Alert(
        building_id=building.id,
        sensor_id=temperature_sensor.id,
        severity=AlertSeverity.critical,
        alert_type=AlertType.threshold,
        message="test",
        status=AlertStatus.active,
    )
    db_session.add(alert)
    db_session.commit()

    mock_conn = MagicMock()
    with (
        patch("app.services.notifications.smtplib.SMTP") as mock_smtp,
        patch("app.services.notifications.urllib.request.urlopen", side_effect=OSError("boom")),
    ):
        mock_smtp.return_value.__enter__.return_value = mock_conn
        notifications.notify_critical_alert(db_session, alert, building)  # no debe lanzar

    mock_conn.send_message.assert_called_once()


def test_staying_critical_does_not_renotify(monkeypatch, client, admin_user, temperature_sensor):
    _configure_smtp(monkeypatch)
    mock_conn = MagicMock()
    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_conn
        client.post(
            "/api/ingest/reading",
            json={
                "sensor_id": temperature_sensor.id,
                "api_key": temperature_sensor.api_key,
                "value": 40.0,
            },
        )
        client.post(
            "/api/ingest/reading",
            json={
                "sensor_id": temperature_sensor.id,
                "api_key": temperature_sensor.api_key,
                "value": 41.0,
            },
        )
    assert mock_conn.send_message.call_count == 1
