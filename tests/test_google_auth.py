"""
Integration tests for POST /auth/google.

Uses an isolated in-memory SQLite database (never touches db_storage/easygov.db)
by overriding the `get_db` dependency on a lightweight app that only mounts the
google auth router. The heavy google-auth network call (certificate fetch) is
replaced with a stub that returns canned claims.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.google_auth as google_auth_module
from app.auth_utils import hash_password
from app.database import get_db
from app.google_auth import router as google_auth_router
from app.models import Base, User

WEB_CLIENT_ID = "test-web-client.apps.googleusercontent.com"
FAKE_CLAIMS = {
    "sub": "google-user-123",
    "email": "ram.shrestha@gmail.com",
    "email_verified": True,
    "name": "Ram Shrestha",
}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_WEB_CLIENT_ID", WEB_CLIENT_ID)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(google_auth_router)
    app.dependency_overrides[get_db] = override_get_db

    # Stub the network-bound verifier so tests never hit Google.
    google_auth_module.id_token.verify_oauth2_token = lambda token, req, aud: FAKE_CLAIMS

    with TestClient(app) as test_client:
        yield test_client, testing_session

    Base.metadata.drop_all(bind=engine)


def _db(client):
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    return db, gen


def _insert_user(session_factory, **kw):
    with session_factory() as db:
        user = User(
            email=kw.get("email", "existing@example.com"),
            password_hash=hash_password("s3cret"),
            full_name=kw.get("full_name", "Existing User"),
            google_id=kw.get("google_id"),
            is_active=kw.get("is_active", True),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def test_google_login_creates_new_user(client):
    test_client, _ = client
    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == FAKE_CLAIMS["email"]
    assert body["user"]["full_name"] == FAKE_CLAIMS["name"]

    db, gen = _db(test_client)
    try:
        user = db.query(User).filter(User.email == FAKE_CLAIMS["email"]).first()
        assert user is not None
        assert user.google_id == FAKE_CLAIMS["sub"]
        assert user.is_active
        # Password/Google-only user must not collide with a real password.
        assert user.password_hash.startswith("$2")
    finally:
        gen.close()


def test_google_login_links_existing_email_account(client):
    test_client, session_factory = client
    _insert_user(session_factory, email=FAKE_CLAIMS["email"], full_name="Pre-existing")

    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == FAKE_CLAIMS["email"]

    db, gen = _db(test_client)
    try:
        user = db.query(User).filter(User.email == FAKE_CLAIMS["email"]).first()
        assert user.google_id == FAKE_CLAIMS["sub"]
        # No duplicate account was created.
        assert db.query(User).count() == 1
    finally:
        gen.close()


def test_google_login_existing_user_by_google_id(client):
    test_client, session_factory = client
    user_id = _insert_user(
        session_factory,
        email="linked@gmail.com",
        full_name="Linked User",
        google_id=FAKE_CLAIMS["sub"],
    )

    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "linked@gmail.com"
    assert body["user"]["id"] == user_id  # the existing row, not a new one


def test_google_login_missing_config_returns_401(client, monkeypatch):
    test_client, _ = client
    monkeypatch.delenv("GOOGLE_OAUTH_WEB_CLIENT_ID")
    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 401
    assert "not configured" in resp.json()["detail"].lower()


def test_google_login_invalid_token_returns_401(client):
    test_client, _ = client

    def _boom(token, req, aud):
        raise ValueError("invalid signature")

    google_auth_module.id_token.verify_oauth2_token = _boom
    resp = test_client.post("/auth/google", json={"id_token": "garbage.token"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_google_login_unverified_email_returns_401(client):
    test_client, _ = client
    google_auth_module.id_token.verify_oauth2_token = lambda t, r, a: {**FAKE_CLAIMS, "email_verified": False}
    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 401


def test_google_login_deactivated_user_returns_403(client):
    test_client, session = client
    _insert_user(
        session,
        email="banned@gmail.com",
        full_name="Banned User",
        google_id=FAKE_CLAIMS["sub"],
        is_active=False,
    )
    resp = test_client.post("/auth/google", json={"id_token": "fake.jwt.token"})
    assert resp.status_code == 403
    assert "deactivated" in resp.json()["detail"].lower()


def test_google_login_missing_id_token_is_422(client):
    test_client, _ = client
    resp = test_client.post("/auth/google", json={})
    assert resp.status_code == 422