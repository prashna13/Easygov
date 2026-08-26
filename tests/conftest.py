"""
Shared test fixtures for the EasyGov backend suite.

Import-time environment isolation (runs before any test module imports the app):

  * EASYGOV_LITE=1        -> skip loading the heavy embeddings/Chroma/LLM stack
  * JWT_SECRET_KEY        -> deterministic signing secret (no db_storage write)
  * DOC_ENCRYPTION_KEY    -> deterministic doc-at-rest key (no db_storage write)
  * EASYGOV_DOC_STORAGE   -> redirect document uploads to a fresh temp dir,
                             so tests NEVER write into the real db_storage/.
"""

import os
import tempfile

import pytest
from cryptography.fernet import Fernet
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("EASYGOV_LITE", "1")
os.environ.setdefault("JWT_SECRET_KEY", "easygov-test-secret")
os.environ.setdefault("DOC_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("EASYGOV_DOC_STORAGE", tempfile.mkdtemp(prefix="easygov_docs_"))

from fastapi.testclient import TestClient  # noqa: E402

from app.auth_utils import create_access_token, hash_password  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app as app_main  # noqa: E402
from app.models import Base, GovService, PrerequisiteRule, User  # noqa: E402

# Titles that the onboarding document keys map to (mirrors ONBOARDING_DOCUMENTS).
SERVICE_TITLES = {
    "citizenship": "Citizenship Certificate Copy",
    "nid": "NID Registration",
    "passport": "E-Passport Apply",
    "driving_license": "Driving License",
}

# The seeded dependency chain (service_title -> prerequisite_title).
PREREQUISITE_RULES = [
    ("NID Registration", "Citizenship Certificate Copy"),
    ("E-Passport Apply", "Citizenship Certificate Copy"),
    ("E-Passport Apply", "NID Registration"),
    ("Driving License", "Citizenship Certificate Copy"),
]


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(db_engine):
    """Session factory bound to the isolated in-memory database."""
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client(db):
    """TestClient over the real FastAPI app with get_db overridden to the
    isolated in-memory database (so the real db_storage/easygov.db is untouched)."""

    def override_get_db():
        session = db()
        try:
            yield session
        finally:
            session.close()

    app_main.dependency_overrides[get_db] = override_get_db
    with TestClient(app_main) as client:
        yield client
    app_main.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def seeded(db):
    """Seed the core catalog + prerequisite chain; returns {title -> id}."""
    with db() as session:
        services = []
        for title in SERVICE_TITLES.values():
            svc = GovService(title=title, category="Test")
            session.add(svc)
            services.append(svc)
        session.flush()

        id_by_title = {s.title: s.id for s in services}
        for service_title, prereq_title in PREREQUISITE_RULES:
            session.add(
                PrerequisiteRule(
                    service_id=id_by_title[service_title],
                    prerequisite_service_id=id_by_title[prereq_title],
                    is_mandatory=True,
                    notes=f"{service_title} requires {prereq_title}",
                )
            )
        session.commit()
        return dict(id_by_title)


@pytest.fixture()
def auth_headers(db):
    """Factory returning Bearer headers for a freshly created test user."""

    def _make(email="user@easygov.np", dob="2000-01-01", is_active=True):
        with db() as session:
            user = User(
                email=email,
                full_name="Test User",
                password_hash=hash_password("secret123"),
                date_of_birth=date.fromisoformat(dob),
                is_active=is_active,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        token = create_access_token({"sub": email})
        return {"Authorization": f"Bearer {token}"}

    return _make


def pytest_sessionfinish(session, exitstatus):
    """Best-effort cleanup of the temp doc-storage dir after the whole run."""
    doc_dir = os.environ.get("EASYGOV_DOC_STORAGE")
    if doc_dir and os.path.isdir(doc_dir):
        import shutil
        shutil.rmtree(doc_dir, ignore_errors=True)
