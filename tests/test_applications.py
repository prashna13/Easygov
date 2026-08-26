"""
Integration tests for the application lifecycle (Layer 7):
POST /api/v1/services/{id}/apply, GET /api/v1/applications,
GET /api/v1/applications/{id}, POST /api/v1/applications/{id}/steps/{n}/complete.

Covers prerequisite blocking, idempotent re-apply, step checklist creation,
step advancement, full-completion (status COMPLETED at 100%), duplicate-step and
re-completion guards, 404s, and cross-user ownership (IDOR).
"""


def test_apply_creates_in_progress_with_steps(client, seeded, auth_headers):
    headers = auth_headers(email="apply@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    resp = client.post(f"/api/v1/services/{service_id}/apply", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["progress_percent"] == 0
    assert len(body["steps"]) >= 1
    assert body["steps"][0]["status"] in ("IN_PROGRESS", "PENDING")


def test_apply_requires_login(client, seeded):
    service_id = seeded["Citizenship Certificate Copy"]
    resp = client.post(f"/api/v1/services/{service_id}/apply")
    assert resp.status_code == 401


def test_apply_blocked_when_prerequisite_unmet(client, seeded, auth_headers):
    headers = auth_headers(email="blocked@test.np")
    passport_id = seeded["E-Passport Apply"]  # requires citizenship + NID
    resp = client.post(f"/api/v1/services/{passport_id}/apply", headers=headers)
    assert resp.status_code == 400
    assert "prerequisites are not met" in resp.json()["detail"].lower()


def test_apply_unknown_service_is_404(client, seeded, auth_headers):
    headers = auth_headers(email="nope@test.np")
    resp = client.post("/api/v1/services/99999/apply", headers=headers)
    assert resp.status_code == 404


def test_apply_is_idempotent(client, seeded, auth_headers):
    headers = auth_headers(email="idem@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    first = client.post(f"/api/v1/services/{service_id}/apply", headers=headers).json()
    second = client.post(f"/api/v1/services/{service_id}/apply", headers=headers).json()
    assert first["application_id"] == second["application_id"]


def test_complete_step_advances_and_completes(client, seeded, auth_headers):
    headers = auth_headers(email="progress@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    app = client.post(f"/api/v1/services/{service_id}/apply", headers=headers).json()
    app_id = app["application_id"]
    total = len(app["steps"])

    # Complete all steps in order; the last response must be COMPLETED @ 100%.
    for n in range(1, total + 1):
        result = client.post(
            f"/api/v1/applications/{app_id}/steps/{n}/complete", headers=headers
        ).json()
    assert result["status"] == "COMPLETED"
    assert result["progress_percent"] == 100


def test_complete_step_twice_is_400(client, seeded, auth_headers):
    headers = auth_headers(email="twice@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    app = client.post(f"/api/v1/services/{service_id}/apply", headers=headers).json()
    app_id = app["application_id"]
    client.post(f"/api/v1/applications/{app_id}/steps/1/complete", headers=headers)
    resp = client.post(f"/api/v1/applications/{app_id}/steps/1/complete", headers=headers)
    assert resp.status_code == 400
    assert "already completed" in resp.json()["detail"].lower()


def test_get_application_not_found(client, seeded, auth_headers):
    headers = auth_headers(email="missing@test.np")
    resp = client.get("/api/v1/applications/99999", headers=headers)
    assert resp.status_code == 404


def test_get_application_ownership(client, seeded, auth_headers):
    # User A starts an application; user B cannot read it (IDOR).
    a = auth_headers(email="owner@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    app = client.post(f"/api/v1/services/{service_id}/apply", headers=a).json()
    b = auth_headers(email="other@test.np")
    resp = client.get(f"/api/v1/applications/{app['application_id']}", headers=b)
    assert resp.status_code == 404


def test_list_applications_requires_auth(client, seeded):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 401


def test_list_applications_returns_own(client, seeded, auth_headers):
    headers = auth_headers(email="mylist@test.np")
    service_id = seeded["Citizenship Certificate Copy"]
    client.post(f"/api/v1/services/{service_id}/apply", headers=headers)
    resp = client.get("/api/v1/applications", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
