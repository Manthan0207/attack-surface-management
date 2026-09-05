from app.core.config import settings


def test_login_success(client):
    response = client.post(
        "/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]


def test_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"email": settings.admin_email, "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_register_requires_admin(client, analyst_headers):
    response = client.post(
        "/auth/register",
        headers=analyst_headers,
        json={
            "email": "newuser@example.com",
            "password": "StrongPass1!",
            "full_name": "New User",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 403


def test_register_success(client, admin_headers):
    response = client.post(
        "/auth/register",
        headers=admin_headers,
        json={
            "email": "new.analyst@example.com",
            "password": "StrongPass1!",
            "full_name": "New Analyst",
            "role": "ANALYST",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.analyst@example.com"
    assert body["role"] == "ANALYST"
    assert body["is_active"] is True


def test_register_duplicate_email(client, admin_headers):
    payload = {
        "email": "dup@example.com",
        "password": "StrongPass1!",
        "full_name": "Dup User",
        "role": "VIEWER",
    }
    assert client.post("/auth/register", headers=admin_headers, json=payload).status_code == 201
    response = client.post("/auth/register", headers=admin_headers, json=payload)
    assert response.status_code == 409


def test_register_password_too_short(client, admin_headers):
    response = client.post(
        "/auth/register",
        headers=admin_headers,
        json={
            "email": "short@example.com",
            "password": "Ab1!",
            "full_name": "Short",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]


def test_register_password_missing_complexity(client, admin_headers):
    response = client.post(
        "/auth/register",
        headers=admin_headers,
        json={
            "email": "weak@example.com",
            "password": "alllowercase1",
            "full_name": "Weak",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"].lower()
