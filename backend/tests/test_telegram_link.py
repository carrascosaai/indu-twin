def test_user_can_link_own_telegram_chat_id(client, admin_headers):
    resp = client.patch(
        "/api/auth/me/telegram", json={"telegram_chat_id": "123456"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["telegram_chat_id"] == "123456"

    me = client.get("/api/auth/me", headers=admin_headers)
    assert me.json()["telegram_chat_id"] == "123456"


def test_user_can_unlink_telegram(client, admin_headers):
    client.patch("/api/auth/me/telegram", json={"telegram_chat_id": "123456"}, headers=admin_headers)
    resp = client.patch("/api/auth/me/telegram", json={"telegram_chat_id": None}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["telegram_chat_id"] is None


def test_link_telegram_requires_auth(client):
    resp = client.patch("/api/auth/me/telegram", json={"telegram_chat_id": "123456"})
    assert resp.status_code == 401
