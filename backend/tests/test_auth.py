def test_setup_status_true_on_empty_instance(client):
    resp = client.get("/api/auth/setup-status")
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is True


def test_setup_status_false_once_a_user_exists(client, admin_user):
    resp = client.get("/api/auth/setup-status")
    assert resp.json()["needs_setup"] is False


def test_register_creates_first_admin(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "founder@test.com", "password": "supersecret123", "full_name": "Founder"},
    )
    assert resp.status_code == 201
    assert "access_token" in resp.json()

    resp = client.get("/api/auth/setup-status")
    assert resp.json()["needs_setup"] is False


def test_register_token_grants_admin_access(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "founder@test.com", "password": "supersecret123", "full_name": "Founder"},
    )
    token = resp.json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_register_rejected_once_a_user_already_exists(client, admin_user):
    resp = client.post(
        "/api/auth/register",
        json={"email": "intruder@test.com", "password": "supersecret123", "full_name": "X"},
    )
    assert resp.status_code == 403


def test_register_rejects_short_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "founder@test.com", "password": "short", "full_name": "Founder"},
    )
    assert resp.status_code == 400


def test_forgot_password_returns_generic_message_for_unknown_email(client):
    resp = client.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})
    assert resp.status_code == 200
    assert "Si existe una cuenta" in resp.json()["message"]


def test_forgot_password_sets_reset_token(client, admin_user, db_session):
    resp = client.post("/api/auth/forgot-password", json={"email": admin_user.email})
    assert resp.status_code == 200
    db_session.refresh(admin_user)
    assert admin_user.reset_token_hash is not None
    assert admin_user.reset_token_expires_at is not None


def test_reset_password_with_valid_token(client, admin_user, db_session):
    from datetime import UTC, datetime, timedelta

    from app.security import generate_password_reset_token

    raw_token, token_hash = generate_password_reset_token()
    admin_user.reset_token_hash = token_hash
    admin_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "brandnewpass123"},
    )
    assert resp.status_code == 200


def test_reset_password_token_is_single_use(client, admin_user, db_session):
    from datetime import UTC, datetime, timedelta

    from app.security import generate_password_reset_token

    raw_token, token_hash = generate_password_reset_token()
    admin_user.reset_token_hash = token_hash
    admin_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "brandnewpass123"},
    )
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "anotherpass456"},
    )
    assert resp.status_code == 400


def test_reset_password_rejects_expired_token(client, admin_user, db_session):
    from datetime import UTC, datetime, timedelta

    from app.security import generate_password_reset_token

    raw_token, token_hash = generate_password_reset_token()
    admin_user.reset_token_hash = token_hash
    admin_user.reset_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_reset_password_rejects_unknown_token(client):
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "brandnewpass123"},
    )
    assert resp.status_code == 400


def test_reset_password_rejects_short_password(client, admin_user, db_session):
    from datetime import UTC, datetime, timedelta

    from app.security import generate_password_reset_token

    raw_token, token_hash = generate_password_reset_token()
    admin_user.reset_token_hash = token_hash
    admin_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    resp = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "short"}
    )
    assert resp.status_code == 400


def test_login_success(client, admin_user):
    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "admin123"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client, admin_user):
    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        "/api/auth/login", json={"email": "nobody@test.com", "password": "whatever"}
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token(client, admin_headers):
    resp = client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"
    assert resp.json()["role"] == "admin"


def test_protected_endpoint_rejects_missing_token(client):
    resp = client.get("/api/polygons")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/api/polygons", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_admin_can_create_polygon(client, admin_headers):
    resp = client.post(
        "/api/polygons",
        headers=admin_headers,
        json={"name": "Nuevo", "center_lat": 40.0, "center_lng": -3.0},
    )
    assert resp.status_code == 201


def test_viewer_cannot_create_polygon(client, viewer_headers):
    resp = client.post(
        "/api/polygons",
        headers=viewer_headers,
        json={"name": "Nuevo", "center_lat": 40.0, "center_lng": -3.0},
    )
    assert resp.status_code == 403


def test_viewer_can_read_polygons(client, viewer_headers, polygon):
    resp = client.get("/api/polygons", headers=viewer_headers)
    assert resp.status_code == 200


def test_ingest_reading_does_not_require_user_token(client, temperature_sensor):
    resp = client.post(
        "/api/ingest/reading",
        json={
            "sensor_id": temperature_sensor.id,
            "api_key": temperature_sensor.api_key,
            "value": 22.5,
        },
    )
    assert resp.status_code == 201


def test_ingest_reading_requires_valid_api_key(client, temperature_sensor):
    resp = client.post(
        "/api/ingest/reading",
        json={"sensor_id": temperature_sensor.id, "api_key": "wrong-key", "value": 22.5},
    )
    assert resp.status_code == 401


def test_ingest_reading_requires_api_key_field(client, temperature_sensor):
    resp = client.post(
        "/api/ingest/reading", json={"sensor_id": temperature_sensor.id, "value": 22.5}
    )
    assert resp.status_code == 422


def test_login_is_rate_limited_after_repeated_failures(client, admin_user):
    for _ in range(5):
        resp = client.post(
            "/api/auth/login", json={"email": "admin@test.com", "password": "wrong"}
        )
        assert resp.status_code == 401

    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "wrong"}
    )
    assert resp.status_code == 429

    # Incluso con la contrasena correcta, sigue bloqueado durante la ventana.
    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "admin123"}
    )
    assert resp.status_code == 429


def test_rate_limit_is_scoped_per_email(client, admin_user, viewer_user):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})

    # Otra cuenta desde el mismo cliente/IP no deberia verse afectada.
    resp = client.post(
        "/api/auth/login", json={"email": "viewer@test.com", "password": "viewer123"}
    )
    assert resp.status_code == 200


def test_successful_login_resets_failure_count(client, admin_user):
    for _ in range(4):
        client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})

    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "admin123"}
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "wrong"}
    )
    assert resp.status_code == 401
