"""
Integration tests for POST /api/v1/onboarding (Layer 6 — onboarding).

Covers age derivation from date_of_birth (so it's not asked again), the payload
age fallback for accounts with no DOB, marking selected documents (plus their
mandatory prerequisites) as COMPLETED, and rejection of unknown document keys.
"""

from datetime import date

from app.auth_utils import create_access_token, hash_password
from app.models import ServiceStatus, User, UserService


def _make_user(db, email, dob="2000-01-01"):
    with db() as session:
        session.add(
            User(
                email=email,
                full_name="Onboarding User",
                password_hash=hash_password("secret123"),
                date_of_birth=date.fromisoformat(dob) if dob else None,
            )
        )
        session.commit()
    token = create_access_token({"sub": email})
    return {"Authorization": f"Bearer {token}"}


def _stored_user(db, email):
    with db() as session:
        return session.query(User).filter(User.email == email).one()


def test_onboarding_derives_age_from_dob(client, db, seeded):
    headers = _make_user(db, "dob@test.np", dob="2000-01-01")
    resp = client.post(
        "/api/v1/onboarding?lang=en",
        headers=headers,
        json={"completed_documents": ["nid"]},
    )
    assert resp.status_code == 200
    user = _stored_user(db, "dob@test.np")
    today = date.today()
    expected = today.year - 2000 - ((today.month, today.day) < (1, 1))
    assert user.age == expected
    assert user.onboarding_completed is True


def test_onboarding_marks_documents_and_prereqs_completed(client, db, seeded):
    headers = _make_user(db, "mark@test.np")
    resp = client.post(
        "/api/v1/onboarding?lang=en",
        headers=headers,
        json={"completed_documents": ["nid"]},
    )
    assert resp.status_code == 200
    nid_id = seeded["NID Registration"]
    citizenship_id = seeded["Citizenship Certificate Copy"]

    with db() as session:
        user = session.query(User).filter(User.email == "mark@test.np").one()
        rows = session.query(UserService).filter(UserService.user_id == user.id).all()
        status = {r.service_id: r.status for r in rows}

    # NID and its mandatory prerequisite (citizenship) are both completed.
    assert status[nid_id] == ServiceStatus.COMPLETED
    assert status[citizenship_id] == ServiceStatus.COMPLETED


def test_onboarding_unknown_document_key_is_400(client, db, seeded):
    headers = _make_user(db, "unknown@test.np")
    resp = client.post(
        "/api/v1/onboarding?lang=en",
        headers=headers,
        json={"completed_documents": ["not_a_service"]},
    )
    assert resp.status_code == 400
    assert "Unknown document keys" in resp.json()["detail"]


def test_onboarding_requires_age_or_dob(client, db, seeded):
    headers = _make_user(db, "nodob@test.np", dob=None)
    resp = client.post(
        "/api/v1/onboarding?lang=en",
        headers=headers,
        json={"completed_documents": ["nid"]},
    )
    assert resp.status_code == 400
    assert "Please enter a valid age" in resp.json()["detail"]


def test_onboarding_uses_payload_age_when_no_dob(client, db, seeded):
    headers = _make_user(db, "payloadage@test.np", dob=None)
    resp = client.post(
        "/api/v1/onboarding?lang=en",
        headers=headers,
        json={"age": 30, "completed_documents": ["nid"]},
    )
    assert resp.status_code == 200
    user = _stored_user(db, "payloadage@test.np")
    assert user.age == 30
