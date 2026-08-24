# EasyGov Nepal — Security Review

**Date:** 2026-08-24
**Scope:** Android app + FastAPI backend
**Verified against:** `app/main.py`, `app/auth_utils.py`, `app/google_auth.py`, `app/models.py`, `app/schemas.py`, `Easygov_mobile` (Manifest, SessionManager, DocumentsFragment, RetrofitClient, build.gradle.kts, res/xml).

---

## Critical architectural correction — read this first

The checklist assumes a **local, on-device encrypted document vault**. **This app does not have one.** Documents are stored on the **FastAPI backend** (`/api/v1/documents`, `models.py` `documents` table + files under `db_storage/documents/`) and are fetched over the network on demand (`DocumentsFragment` → `ApiService.downloadDocument`).

Consequently several "already built" checklist items **do not actually exist**:

| Checklist says "already built" | Reality |
|---|---|
| Files encrypted via `EncryptedFile` + Android Keystore | ❌ **Not present.** Only `EncryptedSharedPreferences` (for the JWT) uses Keystore/MasterKey |
| Biometric / PIN gate before vault access | ❌ **Not present.** No `BiometricPrompt`, no gate. |
| `FLAG_SECURE` blocking screenshots | ❌ **Not present.** Any screen can be captured. |
| Room metadata DB encrypted (SQLCipher) | ❌ **Not present.** No Room at all; metadata lives in backend plaintext SQLite. |

The real sensitive-data surfaces are: **(1) backend document storage + its transport**, **(2) the downloaded temp copies on the device**, **(3) token lifespan**.

---

## Status matrix

Legend: ✅ PASS · ⚠️ PARTIAL · ❌ FAIL · ➖ N/A (not applicable to this architecture)

### 1. Document Vault

| Item | Status | Evidence / Note |
|---|---|---|
| Local encryption at rest (EncryptedFile/Keystore) | ❌ | Not applicable to architecture; token is encrypted but documents are not stored locally. |
| Vault metadata encryption (SQLCipher) | ❌ | Metadata is in backend `documents` table, plaintext SQLite. |
| Biometric / PIN gate | ❌ | No biometrics anywhere in the app. |
| FLAG_SECURE / screenshot block | ❌ | No `FLAG_SECURE`. |
| Auto-lock after inactivity | ❌ | Not present. |
| Clear decrypted bytes promptly | ⚠️ | `DocumentsFragment.showImage` decodes a `Bitmap` held by the dialog for its lifetime; `openPdf` writes bytes to cache. No explicit zeroing. |
| Disable auto-backup | ❌ **fixed** | Was `allowBackup="true"` with empty sample rules. **Set to `false`** (2026-08-24). |
| No thumbnails cached elsewhere | ✅ | Uploads go straight to backend; PDF temp is in app `cacheDir` (app-internal). No media-store exposure. |

### 2. Network / Transit

| Item | Status | Evidence / Note |
|---|---|---|
| HTTPS only, enforced | ❌ | `network_security_config.xml` base-config is `cleartextTrafficPermitted="true"`; app defaults to `http://10.0.2.2:8000/` and lets the user set any URL. Works for local dev, **blocker for deploy**. |
| Certificate pinning | ❌ | No metrics; only a `lang` query interceptor. |
| Short JWT + refresh rotation | ⚠️ **improved** | Was 30-day token, no refresh. **Changed to 30-minute access token** (no refresh yet). |
| Never log tokens / doc content | ✅ | No logging middleware; uvicorn logs method/path only. Google auth logs warn-level only. |

### 3. Backend (FastAPI)

| Item | Status | Evidence / Note |
|---|---|---|
| Auth on every user route + ownership (IDOR) | ✅ | `_get_owned_document` checks `doc.user_id != current_user.id` → 404 (`main.py:387`) on all document routes; `get_current_user` guards everything else. |
| Rate limiting on `/auth` | ❌ | No `slowapi`/`RateLimiter`; no brute-force lockout anywhere. |
| Server-side upload validation | ✅ | MIME whitelist (`ALLOWED_DOC_MIME`), 10 MB cap, empty check, `os.path.basename` sanitization, UUID stored name (`main.py:410-427`). |
| Secrets not in repo | ✅ | `.env` is git-ignored and untracked. |
| SQL injection safety | ✅ | SQLAlchemy ORM with parameter binding throughout; no raw interpolated SQL. |

### 4. Authentication

| Item | Status | Evidence / Note |
|---|---|---|
| Google OAuth server-side verification | ✅ | `google-auth` `verify_oauth2_token` against web client ID + `email_verified` check (`google_auth.py:45-74`). |
| Password hashing (not SHA-256) | ✅ | `bcrypt.hashpw` / `checkpw` (`auth_utils.py:31-41`). |
| Hardcoded JWT secret | ❌ **fixed** | Was `"easygov_super_secret_key_change_in_production_12345"`. **Now random per-process unless `JWT_SECRET_KEY` is set** (2026-08-24) + startup warning. |
| Account lockout / throttling | ❌ | Not present. |

### 5. Privacy / compliance-adjacent

| Item | Status | Evidence / Note |
|---|---|---|
| Data minimization | ⚠️ | `User` stores both `age` and `date_of_birth`; age is derivable. Minor. |
| No analytics/crash SDKs | ✅ | No Crashlytics/Firebase analytics/third-party trackers found. |
| Account deletion story | ⚠️ | `User.documents` has `cascade="all, delete-orphan"` for metadata, but **no deletion endpoint** and on-disk files aren't cleaned on user removal. |

### 6. Dependency / build hygiene

| Item | Status | Evidence / Note |
|---|---|---|
| Libraries up to date | ⚠️ | `androidx.security:security-crypto:1.1.0-alpha06` (alpha); Retrofit 2.9.0 (old); Python deps **unpinned** in `requirements.txt`. Note: Google paused stable security-crypto. |
| `minifyEnabled` + R8 on release | ❌ | `isMinifyEnabled = false` (`build.gradle.kts:25`). |
| Signed release builds, keystore out of repo | ⚠️ | No `signingConfig` defined; release is unsigned by default. |

---

## What was changed (2026-08-24)

1. **`app/auth_utils.py`** — removed the hardcoded JWT signing secret. `SECRET_KEY` now comes from `JWT_SECRET_KEY` env; if unset, a random `secrets.token_urlsafe(48)` key is generated at startup and a warning is logged. Also tightened `ACCESS_TOKEN_EXPIRE_DAYS = 30` → `ACCESS_TOKEN_EXPIRE_MINUTES = 30`.
2. **`Easygov_mobile/app/src/main/AndroidManifest.xml`** — set `android:allowBackup="false"`.

Verified: backend suite **45/45 pass**; Android `assembleDebug` **BUILD SUCCESSFUL**.

---

## Recommended remediation (highest → lowest priority)

**Before any deployment:**
1. **Enforce TLS.** Production: set base-config `cleartextTrafficPermitted="false"`, whitelist only dev domains (keep `10.0.2.2`), and serve the backend behind HTTPS. Add `RetrofitClient` to reject non-`https://` URLs except the two dev hosts. *Blocking* — currently all PII/doc traffic is cleartext-capable.
2. **Add rate limiting + brute-force lockout.** Add `slowapi` (or similar) on `/auth/login`, `/auth/register`, `/auth/google`; track failed attempts and lock out after N.
3. **Stable JWT secret + refresh tokens.** Set a strong `JWT_SECRET_KEY` in `.env`. Consider a short-lived access token plus a refresh token rotation (the token is what guards all document download endpoints).
4. **Set `JWT_SECRET_KEY` in the deployed config.** If omitted, tokens silently invalidate each restart.

**Strongly recommended:**
5. **Encrypt docs at rest on the backend** (e.g., AES via `cryptography`/`cryptography` Fernet per user key) so a DB/file dump isn't readable; metadata columns (label, tags) could also be encrypted or at least scoped per-user directory (already per-user).
6. **Enable R8** (`isMinifyEnabled = true`) + a keep rule file for Gson/Retrofit, and add release signing config with the keystore outside the repo.
7. **Certificate pinning** for the deployed backend (strong for this PII level).
8. **Add `FLAG_SECURE` + a biometric/PIN gate** if you ever move the vault on-device; for the current server-side vault, at minimum add `FLAG_SECURE` on document view, because the plaintext copy is handled on-screen.
9. **Pin Python deps** in `requirements.txt` (or `pyproject.toml`) to reduce supply-chain risk.

**Nice to have / dissertation ethics section:**
10. Account-deletion endpoint that cascades to backend DB rows **and** deletes on-disk files; document the retention policy.
11. Reconsider double-storing `age` + `date_of_birth` (store one, derive the other).
12. Note `uvicorn` binds `0.0.0.0` (`main.py:973`) — fine for LAN phone testing, but avoid port-forwarding it in production.
