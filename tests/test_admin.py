"""
Integration tests for the admin portal (Layer 9):
GET /admin/services, POST /admin/services/{id}, POST /admin/ingest.

The admin routes are gated by require_admin (an ADMIN_TOKEN header). These tests
cover the unconfigured (503), wrong-token (401) and valid-token (200) cases,
plus service-field update, unknown-service 404, and ingest input validation
that fails before any heavy RAG work is triggered.
"""


def test_admin_requires_token_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = client.get("/admin/services")
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()


def test_admin_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.get("/admin/services", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401


def test_admin_rejects_missing_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.get("/admin/services")
    assert resp.status_code == 401


def test_admin_list_services(client, seeded, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.get("/admin/services", headers={"X-Admin-Token": "expected-token"})
    assert resp.status_code == 200
    assert len(resp.json()) == len(seeded)  # one row per seeded service


def test_admin_update_service_fields(client, seeded, monkeypatch, db):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    headers = {"X-Admin-Token": "expected-token"}
    citizenship_id = seeded["Citizenship Certificate Copy"]

    resp = client.post(
        f"/admin/services/{citizenship_id}",
        json={"title": "Citizenship Updated", "fee_npr": 123, "estimated_days": 9, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 200

    detail = client.get(f"/api/v1/services/{citizenship_id}?lang=en").json()["service"]
    assert detail["title"] == "Citizenship Updated"
    assert detail["fee_npr"] == 123
    assert detail["estimated_days"] == 9


def test_admin_update_unknown_service_404(client, seeded, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.post(
        "/admin/services/99999",
        json={"title": "Ghost"},
        headers={"X-Admin-Token": "expected-token"},
    )
    assert resp.status_code == 404


def test_admin_ingest_rejects_bad_extension(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.post(
        "/admin/ingest",
        data={"service": "passport", "version": "1.0", "replace_previous": "false"},
        files={"file": ("notes.exe", b"data", "application/octet-stream")},
        headers={"X-Admin-Token": "expected-token"},
    )
    assert resp.status_code == 415


def test_admin_ingest_rejects_empty_file(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "expected-token")
    resp = client.post(
        "/admin/ingest",
        data={"service": "passport", "version": "1.0", "replace_previous": "false"},
        files={"file": ("guide.pdf", b"", "application/pdf")},
        headers={"X-Admin-Token": "expected-token"},
    )
    assert resp.status_code == 422
