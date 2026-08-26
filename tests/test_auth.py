"""
Integration tests for /auth/register, /auth/login and /auth/me (Layer 4 — auth core).

Covers: date-of-birth requirement, the age gate, duplicate-email rejection,
successful registration/login, invalid credentials, deactivated accounts,
and JWT-protected /auth/me (with/without/with-an-invalid token).
"""

from datetime import date

from app.auth_utils import hash_password
from app.models import User


def _register(client, email="a@test.np", dob="2000-05-10", password="secret123"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "date_of_birth": dob,
        },
    )


def test_register_requires_date_of_birth(client):
    resp = client.post(
        "/auth/register",
        json={"email": "x@test.np", "password": "pw", "full_name": "X"},
    )
    assert resp.status_code == 422


def test_register_rejects_minor(client):
    resp = _register(client, dob="2011-01-01")
    assert resp.status_code == 400
    assert "Minimum age required" in resp.json()["detail"]


def test_register_rejects_future_dob(client):
    resp = _register(client, dob="2030-01-01")
    assert resp.status_code == 400
    assert "future" in resp.json()["detail"].lower()


def test_register_duplicate_email(client):
    assert _register(client, email="dup@test.np").status_code == 201
    resp = _register(client, email="dup@test.np")
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_register_success_returns_token_and_user(client):
    resp = _register(client, email="ok@test.np", dob="2000-05-10")
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "ok@test.np"
    assert body["user"]["onboarding_completed"] is False


def test_login_success(client):
    _register(client, email="login@test.np")
    resp = client.post(
        "/auth/login", json={"email": "login@test.np", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_invalid_credentials(client):
    _register(client, email="bad@test.np")
    resp = client.post(
        "/auth/login", json={"email": "bad@test.np", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@test.np", "password": "pw"}
    )
    assert resp.status_code == 401


def test_login_deactivated_account(client, db):
    with db() as session:
        session.add(
            User(
                email="banned@test.np",
                full_name="Banned",
                password_hash=hash_password("secret123"),
                date_of_birth=date(2000, 1, 1),
                is_active=False,
            )
        )
        session.commit()

    resp = client.post(
        "/auth/login", json={"email": "banned@test.np", "password": "secret123"}
    )
    assert resp.status_code == 403
    assert "deactivated" in resp.json()["detail"].lower()


def test_me_with_valid_token(client, auth_headers):
    headers = auth_headers(email="me@test.np")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.np"


def test_me_without_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_me_with_deactivated_user(client, db):
    with db() as session:
        session.add(
            User(
                email="gone@test.np",
                full_name="Gone",
                password_hash=hash_password("secret123"),
                is_active=False,
            )
        )
        session.commit()
    token = __import__("app.auth_utils", fromlist=["create_access_token"]).create_access_token({"sub": "gone@test.np"})
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
