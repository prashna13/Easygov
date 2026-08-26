# EasyGov Nepal — Test Report

**Date:** 2026-08-25
**Scope:** Backend test suite (FastAPI) + a note on Android/instrumentation tests.
**Status:** 97 tests — **97 passed**, 0 failed (collected in `tests/`).

---

## 1. Methodology

The backend is tested as **black-box HTTP integration tests** using FastAPI's
`TestClient`. Each test mounts the real application and issues real HTTP requests
(`POST /auth/register`, `GET /api/v1/dashboard`, …), then asserts on the HTTP
status code and the JSON response body.

**Isolation guarantees** (so the suite is fast, offline, and never touches real data):

| Concern | How it is isolated |
|---|---|
| Database | An **in-memory SQLite** engine per test; `get_db` is overridden so `db_storage/easygov.db` is never opened. |
| Heavy ML stack | `EASYGOV_LITE=1` skips loading the embedding model, Chroma and the LLM (none are needed by the endpoints under test). |
| JWT signing | `JWT_SECRET_KEY` is fixed → tokens are deterministic and no `db_storage/jwt_secret` is written. |
| Doc encryption | `DOC_ENCRYPTION_KEY` is fixed → decryption is deterministic and no key file is written. |
| **Doc storage** | `EASYGOV_DOC_STORAGE` is redirected to a **fresh temp directory** so uploads never write into the real `db_storage/documents/`. |

Verified: after the run, no new files were created in `db_storage/` and the temp
doc directory was cleaned up by `pytest_sessionfinish`.

### Test layers
| Layer | System under test | Status |
|---|---|---|
| 1 | Geo / haversine + nearby-office filtering | ✅ existing |
| 2 | Chatbot / RAG helpers (`ask_utils`) | ✅ existing |
| 3 | Google Sign-In | ✅ existing |
| 4 | Auth core (register / login / me) | 🆕 Phase 1 |
| 5 | Dashboard + recommendations | 🆕 Phase 1 |
| 6 | Onboarding | 🆕 Phase 1 |
| 7 | Applications & steps | 🆕 Phase 1 |
| 8 | Document vault | 🆕 Phase 1 |
| 9 | Admin portal | 🆕 Phase 1 |

---

## 2. Environment & how to run

```
# from the project root
venv\Scripts\python.exe -m pytest tests -q          # run everything
venv\Scripts\python.exe -m pytest tests/test_auth.py -q   # single module
venv\Scripts\python.exe -m pytest tests --collect-only -q # list tests
```

Fixtures live in `tests/conftest.py`. The env variables are set at import time
inside `conftest.py`, **before** the app is imported, which is why the heavy ML
stack is never loaded during tests.

---

## 3. Coverage matrix

| Layer | Test file | # Tests | Result |
|---|---|---|---|
| 1 | `tests/test_geo.py` | 17 | ✅ |
| 4 | `tests/test_auth.py` | 13 | ✅ |
| 7 | `tests/test_applications.py` | 11 | ✅ |
| 2 | `tests/test_ask_utils.py` | 12 | ✅ |
| 8 | `tests/test_documents.py` | 9 | ✅ |
| 3 | `tests/test_google_auth.py` | 8 | ✅ |
| 9 | `tests/test_admin.py` | 8 | ✅ |
| 6 | `tests/test_onboarding.py` | 5 | ✅ |
| 5 | `tests/test_dashboard.py` | 6 | ✅ |
| — | `tests/test_offices_api.py` | 8 | ✅ |
| **Total** | | **97** | **97 passed** |

---

## 4. Test inventory

### 4.1 Geo (Layer 1) — `tests/test_geo.py` (17)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-GEO-01 | `test_zero_distance` | Haversine of identical points | `0.0` |
| T-GEO-02 | `test_latitude_minute_scale` | 1° latitude ≈ 111.2 km | approx `111.195` |
| T-GEO-03 | `test_kathmandu_to_lalitpur` | Real pair distance | ~`2.4` km |
| T-GEO-04 | `test_kathmandu_to_pokhara` | Long-distance routing | `135 < d < 155` |
| T-GEO-05 | `test_symmetry` | Order independence | `d(a,b) == d(b,a)` |
| T-GEO-06 | `test_london_to_new_york` | Known reference | ~`5570` km |
| T-GEO-07 | `test_radius_constant_sane` | Earth radius constant | `6300–6400` |
| T-GEO-08 | `test_filters_by_service_type` | Tag filtering | only matching office |
| T-GEO-09 | `test_service_type_is_case_insensitive` | Case-insensitive tag | 1 result |
| T-GEO-10 | `test_radius_filters_out_far_offices` | Radius cap | far office excluded |
| T-GEO-11 | `test_larger_radius_includes_more` | Larger radius | more results |
| T-GEO-12 | `test_sorted_nearest_first` | Sort order + distances | ascending distance |
| T-GEO-13 | `test_distance_km_rounded_and_present` | Distance annotated | float present |
| T-GEO-14 | `test_skips_missing_coordinates` | Null-coordinate guard | office dropped |
| T-GEO-15 | `test_empty_result_when_nothing_matches` | No type match | `[]` |
| T-GEO-16 | `test_empty_result_when_nothing_in_radius` | No offices in radius | `[]` |
| T-GEO-17 | `test_blank_service_type_returns_empty` | Blank type | `[]` |

### 4.2 Offices API (Layer 1) — `tests/test_offices_api.py` (8)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-OFF-01 | `test_nearby_returns_sorted_filtered` | Endpoint sorting/filtering | 2 offices, nearest first |
| T-OFF-02 | `test_nearby_narrow_radius` | Radius parameter | 1 result |
| T-OFF-03 | `test_nearby_other_service_type` | Different tag | 1 result |
| T-OFF-04 | `test_nearby_empty_results` | No matching offices | `[]` |
| T-OFF-05 | `test_nearby_missing_service_type_is_422` | Missing param | 422 |
| T-OFF-06 | `test_nearby_invalid_coordinates_are_422` | Out-of-range lat | 422 |
| T-OFF-07 | `test_nearby_zero_radius_is_422` | Invalid radius | 422 |
| T-OFF-08 | `test_nearby_inactive_office_excluded` | Inactive filtered | office absent |

### 4.3 Chatbot / RAG helpers (Layer 2) — `tests/test_ask_utils.py` (12)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-ASK-01 | `test_system_prompts_have_both_variants` | EN + NE prompts, `{context}`/`{question}` | present |
| T-ASK-02 | `test_nepali_prompt_keeps_json_keys_english` | JSON keys stay English | `"answer"/"topic"/"suggest_guide"` |
| T-ASK-03 | `test_parse_valid_json` | Valid JSON parsing | answer + topic parsed |
| T-ASK-04 | `test_parse_code_fenced_json` | ```json fences stripped | parsed |
| T-ASK-05 | `test_parse_malformed_json_falls_back_to_raw_text` | Non-JSON fallback | raw text as answer |
| T-ASK-06 | `test_parse_non_dict_json_falls_back` | JSON list rejected | fallback |
| T-ASK-07 | `test_parse_unknown_topic_is_nulled` | Unknown topic | topic `None` |
| T-ASK-08 | `test_build_response_with_topic_and_guide` | Guide link + service id | populated |
| T-ASK-09 | `test_build_response_suggest_false_omits_guide` | suggest_guide=false | guide omitted |
| T-ASK-10 | `test_build_response_null_topic_omits_guide` | null topic | guide omitted |
| T-ASK-11 | `test_resolve_guide_service_returns_correct_rows` | Topic → real service | correct titles |
| T-ASK-12 | `test_resolve_guide_service_unknown_topic` | Unknown topic | `None` |

### 4.4 Google Sign-In (Layer 3) — `tests/test_google_auth.py` (8)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-GA-01 | `test_google_login_creates_new_user` | Auto-register new user | 200 + bcrypt hash |
| T-GA-02 | `test_google_login_links_existing_email_account` | Link to existing email | no duplicate |
| T-GA-03 | `test_google_login_existing_user_by_google_id` | Reuse by google_id | same user id |
| T-GA-04 | `test_google_login_missing_config_returns_401` | Env not set | 401 |
| T-GA-05 | `test_google_login_invalid_token_returns_401` | Bad signature | 401 |
| T-GA-06 | `test_google_login_unverified_email_returns_401` | unverified email | 401 |
| T-GA-07 | `test_google_login_deactivated_user_returns_403` | Inactive account | 403 |
| T-GA-08 | `test_google_login_missing_id_token_is_422` | Missing id_token | 422 |

### 4.5 Auth core (Layer 4) — `tests/test_auth.py` (13)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-AUTH-01 | `test_register_requires_date_of_birth` | DOB is required | 422 |
| T-AUTH-02 | `test_register_rejects_minor` | Age gate (<16) | 400 "Minimum age required" |
| T-AUTH-03 | `test_register_rejects_future_dob` | Future DOB guard | 400 |
| T-AUTH-04 | `test_register_duplicate_email` | Unique email | 400 "already exists" |
| T-AUTH-05 | `test_register_success_returns_token_and_user` | Happy path | 201 + JWT + user |
| T-AUTH-06 | `test_login_success` | Valid login | 200 + token |
| T-AUTH-07 | `test_login_invalid_credentials` | Wrong password | 401 |
| T-AUTH-08 | `test_login_unknown_user` | Unknown email | 401 |
| T-AUTH-09 | `test_login_deactivated_account` | Inactive account | 403 "deactivated" |
| T-AUTH-10 | `test_me_with_valid_token` | JWT-protected `/auth/me` | 200 + email |
| T-AUTH-11 | `test_me_without_token` | No token | 401 |
| T-AUTH-12 | `test_me_with_invalid_token` | Malformed token | 401 |
| T-AUTH-13 | `test_me_with_deactivated_user` | Inactive user token | 401 |

### 4.6 Dashboard & recommendations (Layer 5) — `tests/test_dashboard.py` (6)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-DASH-01 | `test_dashboard_guest_returns_catalog` | Guest view | "Guest User", services ≥4 |
| T-DASH-02 | `test_dashboard_requires_onboarding_flag_when_unonboarded` | Onboarding flag | `needs_onboarding=true` |
| T-DASH-03 | `test_dashboard_recommendations_exclude_completed` | No completed services | completed titles absent |
| T-DASH-04 | `test_dashboard_recommended_next_step_after_citizenship` | Chain next step | `NID Registration` |
| T-DASH-05 | `test_dashboard_ranked_actionable_first` | Prereq-aware ranking | NID (met) before E-Passport (unmet) |
| T-DASH-06 | `test_dashboard_localized_falls_back_to_english` | NE fallback | 200, EN titles |

### 4.7 Onboarding (Layer 6) — `tests/test_onboarding.py` (5)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-OB-01 | `test_onboarding_derives_age_from_dob` | Age derived, not re-asked | stored age matches DOB |
| T-OB-02 | `test_onboarding_marks_documents_and_prereqs_completed` | Prereq resolution | NID **and** citizenship COMPLETED |
| T-OB-03 | `test_onboarding_unknown_document_key_is_400` | Unknown key | 400 |
| T-OB-04 | `test_onboarding_requires_age_or_dob` | No age, no DOB | 400 "valid age" |
| T-OB-05 | `test_onboarding_uses_payload_age_when_no_dob` | age fallback | stored age = payload |

### 4.8 Applications & steps (Layer 7) — `tests/test_applications.py` (11)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-APP-01 | `test_apply_creates_in_progress_with_steps` | Apply happy path | IN_PROGRESS + steps |
| T-APP-02 | `test_apply_requires_login` | Auth required | 401 |
| T-APP-03 | `test_apply_blocked_when_prerequisite_unmet` | Prereq gate | 400 "prerequisites are not met" |
| T-APP-04 | `test_apply_unknown_service_is_404` | Unknown service | 404 |
| T-APP-05 | `test_apply_is_idempotent` | Re-apply returns same app | same `application_id` |
| T-APP-06 | `test_complete_step_advances_and_completes` | Step → full completion | COMPLETED @ 100% |
| T-APP-07 | `test_complete_step_twice_is_400` | Re-complete step | 400 "already completed" |
| T-APP-08 | `test_get_application_not_found` | Missing app | 404 |
| T-APP-09 | `test_get_application_ownership` | **IDOR** — other user | 404 |
| T-APP-10 | `test_list_applications_requires_auth` | List endpoint auth | 401 |
| T-APP-11 | `test_list_applications_returns_own` | List returns own | 1 item |

### 4.9 Document vault (Layer 8) — `tests/test_documents.py` (9)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-DOC-01 | `test_upload_requires_login` | Auth required | 401 |
| T-DOC-02 | `test_upload_requires_label` | Label required | 422 |
| T-DOC-03 | `test_upload_rejects_unsupported_mime` | MIME whitelist | 415 |
| T-DOC-04 | `test_upload_rejects_empty_file` | Empty file guard | 422 |
| T-DOC-05 | `test_upload_success_and_list` | Upload + list | 201, list has 1 |
| T-DOC-06 | `test_upload_stores_encrypted_not_plaintext` | At-rest encryption | disk ≠ plaintext |
| T-DOC-07 | `test_download_round_trip_matches_original` | Encrypt→decrypt round trip | bytes equal |
| T-DOC-08 | `test_download_idor_other_user_404` | **IDOR** — other user | 404 |
| T-DOC-09 | `test_delete_removes_row_and_file` | Delete cleans DB + disk | row gone, file gone |

### 4.10 Admin portal (Layer 9) — `tests/test_admin.py` (8)

| ID | Test | Verifies | Expected |
|---|---|---|---|
| T-ADM-01 | `test_admin_requires_token_configured` | Env unset | 503 "not configured" |
| T-ADM-02 | `test_admin_rejects_wrong_token` | Wrong token | 401 |
| T-ADM-03 | `test_admin_rejects_missing_token` | Missing token | 401 |
| T-ADM-04 | `test_admin_list_services` | List for admin | 200, all services |
| T-ADM-05 | `test_admin_update_service_fields` | Field update (no RAG) | updated title/fee/days |
| T-ADM-06 | `test_admin_update_unknown_service_404` | Unknown service | 404 |
| T-ADM-07 | `test_admin_ingest_rejects_bad_extension` | Extension guard | 415 |
| T-ADM-08 | `test_admin_ingest_rejects_empty_file` | Empty file guard | 422 |

---

## 5. Results

| Metric | Value |
|---|---|
| Tests collected | 97 |
| **Passed** | **97** |
| Failed | 0 |
| Runtime | ~10 s |
| `db_storage/` side-effects | **None** (verified) |

---

## 6. Change log

- **2026-08-19** — baseline unit/integration suite (geo, offices API, google auth, ask utils).
- **2026-08-25 (Phase 1)** — added backend coverage for Layers 4–9:
  - `tests/test_auth.py` (13), `tests/test_dashboard.py` (6), `tests/test_onboarding.py` (5),
    `tests/test_applications.py` (11), `tests/test_documents.py` (9), `tests/test_admin.py` (8).
  - Enabled test isolation: `app/main.py` now reads `EASYGOV_LITE` (skips heavy ML load)
    and `EASYGOV_DOC_STORAGE` (redirects uploads to a temp dir); `tests/conftest.py`
    sets fixed JWT + encryption keys and provides shared in-memory fixtures.
- **Next phases:** Phase 2 = RAGAS chatbot evaluation; Phase 3 = Android unit + UI tests and CI.
