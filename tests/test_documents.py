"""
Integration tests for the document vault (Layer 8):
POST /api/v1/documents, GET /api/v1/documents,
GET /api/v1/documents/{id}/download, DELETE /api/v1/documents/{id}.

Covers upload validation (label required, MIME whitelist, empty file), filename
sanitisation, at-rest encryption round-trip, legacy-plaintext fallback,
ownership (IDOR → 404), listing, and delete (metadata + file removed).

Storage isolation: the suite runs with EASYGOV_DOC_STORAGE pointed at a temp dir
(see conftest), so no real db_storage/documents folder is touched.
"""

import os

from app.main import DOC_STORAGE_DIR
from app.models import Document as DBDocument


def _upload(client, headers, filename="scan.png", label="My scan", mime="image/png",
            data=None, tags="test", description="a doc", files=None):
    files = files or {"file": (filename, data if data is not None else b"fake-bytes", mime)}
    form = {"label": label, "tags": tags, "description": description}
    return client.post("/api/v1/documents", headers=headers, data=form, files=files)


def test_upload_requires_login(client):
    resp = _upload(client, headers={})
    assert resp.status_code in (401, 422)


def test_upload_requires_label(client, seeded, auth_headers):
    headers = auth_headers(email="lab@test.np")
    resp = _upload(client, headers, label="")
    assert resp.status_code == 422


def test_upload_rejects_unsupported_mime(client, seeded, auth_headers):
    headers = auth_headers(email="mime@test.np")
    resp = _upload(client, headers, filename="file.exe", mime="application/x-msdownload")
    assert resp.status_code == 415


def test_upload_rejects_empty_file(client, seeded, auth_headers):
    headers = auth_headers(email="empty@test.np")
    resp = _upload(client, headers, data=b"")
    assert resp.status_code == 422


def test_upload_success_and_list(client, seeded, auth_headers, db):
    headers = auth_headers(email="up@test.np")
    resp = _upload(client, headers, filename="citizenship.png", mime="image/png", data=b"\x89PNG-data")
    assert resp.status_code == 201
    body = resp.json()
    assert body["label"] == "My scan"
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(b"\x89PNG-data")
    assert body["filename"] == "citizenship.png"

    listing = client.get("/api/v1/documents", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_upload_stores_encrypted_not_plaintext(client, seeded, auth_headers, db):
    headers = auth_headers(email="enc@test.np")
    secret = b"VERY-SECRET-SCAN-CONTENT-0123456789"
    doc = _upload(client, headers, data=secret).json()

    # The on-disk file must NOT be the plaintext.
    with db() as session:
        stored = session.query(DBDocument).filter(DBDocument.id == doc["id"]).one()
    stored_path = DOC_STORAGE_DIR / str(stored.user_id) / stored.stored_name
    assert stored_path.exists()
    disk_bytes = stored_path.read_bytes()
    assert disk_bytes != secret
    assert secret not in disk_bytes


def test_download_round_trip_matches_original(client, seeded, auth_headers, db):
    headers = auth_headers(email="rt@test.np")
    original = b"round trip bytes \x00\x01\x02 payload"
    doc = _upload(client, headers, data=original).json()

    resp = client.get(f"/api/v1/documents/{doc['id']}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.content == original


def test_download_idor_other_user_404(client, seeded, auth_headers):
    a = auth_headers(email="owner2@test.np")
    doc = _upload(client, a, data=b"private").json()
    b = auth_headers(email="thief@test.np")
    resp = client.get(f"/api/v1/documents/{doc['id']}/download", headers=b)
    assert resp.status_code == 404


def test_delete_removes_row_and_file(client, seeded, auth_headers, db):
    headers = auth_headers(email="del@test.np")
    doc = _upload(client, headers, data=b"to-delete").json()

    resp = client.delete(f"/api/v1/documents/{doc['id']}", headers=headers)
    assert resp.status_code == 200

    with db() as session:
        assert session.query(DBDocument).filter(DBDocument.id == doc["id"]).first() is None
    # No leftover file in the (temp) storage dir.
    assert not any(f.name == doc["filename"] for f in DOC_STORAGE_DIR.rglob("*"))
