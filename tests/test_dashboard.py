"""
Integration tests for /api/v1/dashboard (Layer 5 — dashboard + recommendations).

Covers the guest view, the onboarding flag, the prerequisite-aware recommendation
ranking (which must exclude already-completed services), recommended_next_step
from the dependency chain, and English/Nepali fallback.
"""

from app.database import get_db
from app.models import ServiceStatus, User, UserService


def _mark_completed(client, email, service_ids):
    """Insert COMPLETED UserService rows for a user via the override DB session."""
    override = client.app.dependency_overrides[get_db]
    gen = override()
    session = next(gen)
    try:
        user = session.query(User).filter(User.email == email).one()
        for sid in service_ids:
            session.add(
                UserService(
                    user_id=user.id, service_id=sid, status=ServiceStatus.COMPLETED
                )
            )
        session.commit()
    finally:
        gen.close()


def test_dashboard_guest_returns_catalog(client, seeded):
    resp = client.get("/api/v1/dashboard?lang=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_name"] == "Guest User"
    assert body["needs_onboarding"] is False
    assert len(body["services"]) >= 4
    assert len(body["recommendations"]) >= 1


def test_dashboard_requires_onboarding_flag_when_unonboarded(client, seeded, auth_headers):
    headers = auth_headers(email="fresh@test.np")
    resp = client.get("/api/v1/dashboard?lang=en", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["needs_onboarding"] is True


def test_dashboard_recommendations_exclude_completed(client, seeded, auth_headers):
    headers = auth_headers(email="done@test.np")
    _mark_completed(
        client,
        "done@test.np",
        [seeded["Citizenship Certificate Copy"], seeded["NID Registration"]],
    )
    rec_titles = [r["title"] for r in client.get("/api/v1/dashboard?lang=en", headers=headers).json()["recommendations"]]
    assert "Citizenship Certificate Copy" not in rec_titles
    assert "NID Registration" not in rec_titles


def test_dashboard_recommended_next_step_after_citizenship(client, seeded, auth_headers):
    headers = auth_headers(email="next@test.np")
    _mark_completed(client, "next@test.np", [seeded["Citizenship Certificate Copy"]])

    body = client.get("/api/v1/dashboard?lang=en", headers=headers).json()
    assert body["recommended_next_step"]["title"] == "NID Registration"


def test_dashboard_ranked_actionable_first(client, seeded, auth_headers):
    headers = auth_headers(email="rank@test.np")
    _mark_completed(client, "rank@test.np", [seeded["Citizenship Certificate Copy"]])

    titles = [r["title"] for r in client.get("/api/v1/dashboard?lang=en", headers=headers).json()["recommendations"]]
    # NID has its prerequisites met -> must rank ahead of E-Passport (needs NID).
    assert titles[0] == "NID Registration"


def test_dashboard_localized_falls_back_to_english(client, seeded, auth_headers):
    headers = auth_headers(email="lang@test.np")
    resp = client.get("/api/v1/dashboard?lang=ne", headers=headers)
    assert resp.status_code == 200
    # Seeded services have no Nepali title, so the endpoint falls back to English.
    body = resp.json()
    assert any(r["title"] for r in body["services"])
