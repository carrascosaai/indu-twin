def test_admin_can_list_users(client, admin_headers, admin_user, viewer_user):
    resp = client.get("/api/users", headers=admin_headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert {"admin@test.com", "viewer@test.com"} <= emails


def test_viewer_cannot_list_users(client, viewer_headers):
    resp = client.get("/api/users", headers=viewer_headers)
    assert resp.status_code == 403


def test_admin_can_create_user(client, admin_headers):
    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "nuevo@test.com",
            "password": "secreto123",
            "full_name": "Nuevo Usuario",
            "role": "viewer",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "nuevo@test.com"
    assert body["role"] == "viewer"
    assert "password" not in body
    assert "hashed_password" not in body


def test_cannot_create_duplicate_email(client, admin_headers, admin_user):
    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "admin@test.com", "password": "x", "full_name": "Dup"},
    )
    assert resp.status_code == 409


def test_admin_can_change_role(client, admin_headers, viewer_user):
    resp = client.patch(
        f"/api/users/{viewer_user.id}", headers=admin_headers, json={"role": "admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_admin_can_reset_another_users_password(client, admin_headers, viewer_user):
    resp = client.patch(
        f"/api/users/{viewer_user.id}",
        headers=admin_headers,
        json={"password": "newpassword123"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/auth/login",
        json={"email": viewer_user.email, "password": "newpassword123"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/auth/login", json={"email": viewer_user.email, "password": "viewer123"}
    )
    assert resp.status_code == 401


def test_password_reset_rejects_short_password(client, admin_headers, viewer_user):
    resp = client.patch(
        f"/api/users/{viewer_user.id}", headers=admin_headers, json={"password": "short"}
    )
    assert resp.status_code == 400


def test_viewer_cannot_reset_password(client, viewer_headers, admin_user):
    resp = client.patch(
        f"/api/users/{admin_user.id}",
        headers=viewer_headers,
        json={"password": "newpassword123"},
    )
    assert resp.status_code == 403


def test_admin_cannot_demote_themselves(client, admin_headers, admin_user):
    resp = client.patch(
        f"/api/users/{admin_user.id}", headers=admin_headers, json={"role": "viewer"}
    )
    assert resp.status_code == 400


def test_admin_can_delete_other_user(client, admin_headers, viewer_user):
    resp = client.delete(f"/api/users/{viewer_user.id}", headers=admin_headers)
    assert resp.status_code == 204
    resp = client.get("/api/users", headers=admin_headers)
    assert viewer_user.id not in [u["id"] for u in resp.json()]


def test_admin_cannot_delete_themselves(client, admin_headers, admin_user):
    resp = client.delete(f"/api/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 400
