# EasyGov Nepal — Project Progress Log

> **Purpose**: This is a living document. Update it every time a new feature is completed.
> Share this file with any LLM at the start of a session so it can pick up exactly where you left off.

---

## Project Identity

| Field | Value |
|---|---|
| **Project name** | EasyGov Nepal |
| **Type** | Dissertation / Research project |
| **Goal** | AI-powered civic assistant helping Nepali citizens navigate government services |
| **Root directory** | `c:\Users\Ivy\Desktop\EasyGov_project` |
| **Workspace corpus** | `prashna13/Easygov` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python · FastAPI · Uvicorn |
| AI / RAG | LangChain · ChromaDB · HuggingFace Embeddings · OpenRouter (gpt-oss-120b) |
| ORM / DB | SQLAlchemy 2.x · SQLite (`db_storage/easygov.db`) |
| Auth | JWT via `python-jose` · direct bcrypt password hashing · **Google Sign-In (`google-auth` + `play-services-auth`)** |
| Dev web UI | Streamlit |
| Mobile | Android (Kotlin/Java) · Retrofit2 · Markwon · Material Design |
| Embedding model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |

---

## Repository Structure

```
EasyGov_project/
├── .env                        # OPENROUTER_API_KEY (set)
├── requirements.txt            # All Python dependencies (includes email-validator, python-jose, bcrypt)
├── PROGRESS.md                 # <-- YOU ARE HERE
├── app/
│   ├── database.py             # [DONE] SQLAlchemy engine + get_db() dependency
│   ├── models.py               # [DONE] 6 ORM models (users, chat_messages, gov_services, prerequisite_rules, user_services, progress)
│   ├── schemas.py              # [DONE] Pydantic schemas (auth, dashboard, onboarding, application progress)
│   ├── auth_utils.py           # [DONE] Password hashing, JWT token encoding/decoding, get_current_user dependencies
│   ├── migrate.py              # [DONE] Table creation script (idempotent)
│   ├── seed_data.py            # [DONE] Seed script (re-runnable, skip-on-duplicate)
│   ├── nepali_content.py       # [DONE] Generated Nepali translations (SERVICE_NE, STEP_TEMPLATES_NE, SEED_STEPS_NE)
│   ├── translate_seed.py       # [DONE] LLM translation generator → nepali_content.py
│   ├── main.py                 # FastAPI app — /ask, auth, dashboard, onboarding, service detail, application progress, offices endpoints
│   ├── ingest_data.py          # PDF/MD ingestion pipeline → ChromaDB
│   ├── frontend.py             # Streamlit web UI (dev/demo only)
│   ├── geo.py                  # [DONE] Haversine distance + find_nearby_offices (used by /api/v1/offices/nearby)
│   ├── offices.py              # [DONE] Nearby-offices FastAPI router (GET /api/v1/offices/nearby)
│   ├── google_auth.py          # [DONE] Google ID-token verification + POST /auth/google router (auto-creates/links users by email)
│   ├── office_seed_data.py     # [DONE] Static curated catalog of 34 Nepali government offices (DAOs, passport/NID centers, DOTM, muncipalities)
│   └── db_handeler.py          # [EMPTY PLACEHOLDER] — not implemented yet
├── db_storage/
│   ├── easygov.db              # [DONE] Main SQLite database (users, services, progress)
│   ├── chroma_db/              # ChromaDB vector store (passport + NID docs ingested)
│   └── record_manager.db       # LangChain incremental indexing tracker
├── data_source/
│   ├── Passport/               # 4 PDFs + 2 Markdown files
│   └── NID/                    # 4 PDFs
└── Easygov_mobile/             # Android app (Kotlin)
    └── app/src/main/
        ├── java/com/example/easygov/
        │   ├── MainActivity.kt          # [DONE] Bottom nav: Chat / Dashboard / Profile
        │   ├── ChatFragment.kt          # [DONE] RAG chat + Markwon, history & new-chat buttons
        │   ├── DashboardFragment.kt     # [DONE] Uses stored Bearer token from SessionManager, real DB data
        │   ├── LoginFragment.kt         # [DONE] Calls POST /auth/login + Google Sign-In (POST /auth/google), saves JWT via SessionManager
        │   ├── RegisterFragment.kt      # [DONE] Calls POST /auth/register, auto-login after signup
        │   ├── ProfileFragment.kt       # [DONE] Full profile from /auth/me + "My Applications & Progress" list
        │   ├── ApplicationsAdapter.kt   # [DONE] Profile application cards (title/status/progress %) → open tracker
        │   ├── ServiceDetailFragment.kt # [DONE] Detail + guide + prereq blocking; Apply Now starts an application; "Find Nearest Office" button → NearbyOfficesFragment
        │   ├── NearbyOfficesFragment.kt # [DONE] Finds nearest offices — on-demand coarse location (permission + single-fix with timeout), API call, list/empty/error/permission states, Directions → Google Maps
        │   ├── OfficeAdapter.kt        # [DONE] Nearby-office cards (name/type/address/meta/distance + Directions button)
        │   ├── ApplicationProgressFragment.kt # [DONE] Step checklist + progress bar; ticks steps complete
        │   ├── ProgressStepAdapter.kt    # [DONE] Checklist adapter (current step tappable only)
        │   ├── DashboardAdapter.kt
        │   ├── ChatHistoryAdapter.kt    # [DONE] Adapter for chat history bottom sheet
        │   ├── ChatHistoryBottomSheet.kt# [DONE] Fetches /chat/history, newest-first list
        │   ├── SessionManager.kt        # AES256 encrypted token storage
        │   ├── LocaleManager.kt         # [DONE] Persists app language (SharedPreferences) + applies locale
        │   ├── EasyGovApp.kt            # [DONE] Application class — inits Retrofit + stored locale on launch
        │   ├── ChatNetworkInterface.kt  # ChatRequest/ChatResponse/ChatHistoryResponse DTOs
        │   ├── model/
        │   │   ├── GovService.kt
        │   │   ├── DashboardResponse.kt
        │   │   ├── OnboardingModels.kt    # [DONE] Onboarding request/response + ServiceDetailResponse (includes application)
        │   │   ├── Office.kt             # [DONE] GovernmentOfficeOut DTO (with distance_km)
        │   │   ├── ApplicationModels.kt   # [DONE] ApplicationProgress + ProgressStep DTOs
        │   │   └── AuthModels.kt        # [DONE] LoginRequest, RegisterRequest, GoogleLoginRequest, TokenResponse, UserOut
        │   └── network/
        │       ├── ApiService.kt        # [DONE] Endpoints: dashboard, onboarding, services, apply, applications, steps, /ask, /chat/history, /auth/*, documents, offices/nearby
        │       └── RetrofitClient.kt    # [DONE] Base URL: http://10.0.2.2:8000/ (Emulator standard)
        └── res/layout/
            ├── activity_main.xml
            ├── fragment_chat.xml
            ├── fragment_dashboard.xml
            ├── fragment_login.xml
            ├── fragment_register.xml
            ├── fragment_profile.xml
            ├── item_application_card.xml
            ├── fragment_service_detail.xml
            ├── fragment_application_progress.xml
            ├── item_progress_step.xml
            ├── bottom_sheet_chat_history.xml
            ├── item_dashboard_card.xml
            ├── item_chat_history.xml
            ├── item_office.xml               # [DONE] Nearby-office card (Directions button)
            ├── fragment_nearby_offices.xml   # [DONE] Nearby-offices screen (header, list, loading/empty/error/permission states)
            └── values-ne/strings.xml     # [DONE] Full Nepali UI strings
```

---

## Seed Test Account Credentials

| Field | Value |
|---|---|
| Name | Prashna KC |
| Email | `prashna@easygov.np` |
| Password | `password123` |
| Citizenship No. | 12-01-78-12345 |
| Province | Bagmati Province |

---

## API Endpoints Status

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| GET | `/` | LIVE | Health check |
| POST | `/ask` | LIVE | RAG chatbot — question → ChromaDB → LLM → **concise JSON answer** (`{answer, topic, suggest_guide}`) + `sources` + optional `guide_link`/`guide_service_id` deep-link to a full guide (topic ∈ citizenship/nid/passport/driving_license); detects query language (`langdetect`) and answers in the query's language; malformed LLM JSON falls back to raw text |
| POST | `/auth/register` | LIVE | Creates user, hashes password with bcrypt, returns JWT token |
| POST | `/auth/login` | LIVE | Verifies bcrypt password, returns JWT token + user profile |
| POST | `/auth/google` | LIVE | Google Sign-In — verifies `{id_token}` audience/signature via `google-auth`, auto-creates account (or links to existing email), returns JWT token + profile; requires `GOOGLE_OAUTH_WEB_CLIENT_ID` env |
| GET | `/auth/me` | LIVE | Protected — full profile: name, email, phone, citizenship no., province, age, DOB, address, onboarding status |
| GET | `/api/v1/applications` | LIVE | Protected — all user applications (title, status, progress %, steps), newest first; drives profile progress list |
| GET | `/api/v1/dashboard` | LIVE | Real DB query from SQLite `gov_services` — 4 active services with official guidance (personalizes if Bearer token present) |
| POST | `/api/v1/onboarding` | LIVE | First-login onboarding: age + owned documents → marks services completed, unlocks personalized chain |
| GET | `/api/v1/services/{service_id}` | LIVE | Service detail + `guidance` + `prerequisites_met` / `missing_prerequisites` + existing `application` (drives Android blocked flow) |
| POST | `/api/v1/services/{service_id}/apply` | LIVE | Starts an application → creates `user_service` (IN_PROGRESS) + step checklist from `STEP_TEMPLATES` (idempotent, prerequisite-checked) |
| GET | `/api/v1/applications/{application_id}` | LIVE | Protected — returns an application with step-level progress % |
| POST | `/api/v1/applications/{application_id}/steps/{step_number}/complete` | LIVE | Marks a step COMPLETED, advances next pending step; completes application when all steps done |
| GET | `/chat/history` | LIVE | Protected — returns saved chat history for the authenticated user |
| GET | `/api/v1/user/progress` | NOT BUILT | Replaced by `/api/v1/applications` (aggregate) + `/api/v1/applications/{id}` (detail) |
| GET | `/api/v1/offices/nearby` | LIVE | Public — curated government offices serving `service_type` (citizenship/nid/passport/driving_license) within `radius` km (default 10, max 100) of `lat`/`lng`, sorted nearest-first with haversine `distance_km`; static seeded catalog (no live Google Places) |
| PATCH | `/api/v1/user/services/{service_id}/progress/{step_id}` | NOT BUILT | Superseded by `POST /api/v1/applications/{id}/steps/{n}/complete` (build separately if desired) |

**Language support**: All user-facing endpoints (`/api/v1/dashboard`, `/api/v1/onboarding`, `/api/v1/services/{id}`, `/api/v1/services/{id}/apply`, `/api/v1/applications`, `/api/v1/applications/{id}`, `/api/v1/applications/{id}/steps/{n}/complete`) accept an optional `lang=en|ne` query param (default `en`). Nepali content is stored in `gov_services.title_ne/category_ne/description_ne/guidance_ne` and `progress.step_name_ne/step_description_ne`; the Android `RetrofitClient` interceptor appends `lang` automatically from the selected app language. `/ask` and `/chat/history` are unaffected.

---

## What Is Done

- [x] FastAPI backend with RAG `/ask` endpoint
- [x] ChromaDB vector store populated with Passport + NID PDFs
- [x] Multilingual embedding model (handles Nepali + English)
- [x] Streamlit dev UI connecting to backend
- [x] Android app UI & navigation (Chat, Dashboard, Login, ServiceDetail)
- [x] Encrypted JWT session storage (`SessionManager`) on Android
- [x] SQL database schema & SQLite database (`db_storage/easygov.db`)
- [x] **FastAPI Auth Endpoints**: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- [x] **Real DB-backed Dashboard**: `GET /api/v1/dashboard` queries SQLite `gov_services`
- [x] **Android Auth Integration**: `LoginFragment` makes real call to `/auth/login`, saves JWT in `SessionManager`, and transitions to `DashboardFragment`
- [x] **Android Dashboard Integration**: `DashboardFragment` sends saved Bearer token to personalize welcoming title and recommendations
- [x] **Android Registration**: `RegisterFragment` calls `/auth/register`, saves JWT, auto-login to dashboard
- [x] **Android Profile & Logout**: `ProfileFragment` shows saved user info, `btnLogout` clears `SessionManager`
- [x] **Chat History Backend**: `GET /chat/history` persists + returns user's messages from `chat_messages` table
- [x] **Chat History UI**: `ChatHistoryBottomSheet` + adapter fetch and display saved history (newest first)
- [x] **Onboarding Backend**: `POST /api/v1/onboarding` — saves age, marks owned documents (+ mandatory prerequisites) COMPLETED via dependency rules, returns recommended next step
- [x] **Prerequisite Blocking Backend**: `GET /api/v1/services/{id}` returns `prerequisites_met` + `missing_prerequisites`; dashboard returns `needs_onboarding` + `recommended_next_step`
- [x] **Android Onboarding**: `OnboardingFragment` (age + document checklist) auto-shown when `needs_onboarding` is true; submits to backend then refreshes dashboard
- [x] **Android Next-Step Banner**: Dashboard shows a tappable "Recommended Next Step" banner; service cards open `ServiceDetailFragment` with real service id
- [x] **Android Blocked Service Flow**: `ServiceDetailFragment` fetches prerequisite status; blocked services show a warning panel with read-only informational mode
- [x] **Real Services + Guidance**: Dashboard now shows 4 real services (Citizenship, NID, E-Passport, Driving License) with official guide content (prerequisites, documents, procedure, fees, processing time, resources) stored in `gov_services.guidance` and rendered on the service detail screen
- [x] **Dependency Chain Rebuilt**: Rules now follow the guide's chain — Citizenship (root) → NID → Passport / Driving License; filler services (Bluebook, Business, Birth) retained but inactive
- [x] **Application Progress Backend**: `POST /api/v1/services/{id}/apply` starts an application (creates `user_service` + step checklist from per-service `STEP_TEMPLATES`); `GET /api/v1/applications/{id}` returns progress %; `POST .../steps/{n}/complete` ticks steps and auto-completes the application; service detail now returns the user's existing `application`
- [x] **Android Application Progress**: "Apply Now" on the service detail starts an application (or opens "View My Application"); new `ApplicationProgressFragment` shows status chip, progress bar + %, and a tappable step checklist that marks steps complete via the backend
- [x] **Rich Profile Backend**: `/auth/me` now returns full profile (age, DOB, address, onboarding status); new `GET /api/v1/applications` returns all user applications with progress %
- [x] **Android Profile Page**: `ProfileFragment` shows full personal info from `/auth/me` plus a "My Applications & Progress" list (status chips + progress bars) that opens each application's tracker; logout retained; APK built
- [x] **Nepali Content Generation**: `translate_seed.py` calls OpenRouter LLM to produce verified Devanagari translations for all 4 services + step templates + seed steps → `app/nepali_content.py` (SERVICE_NE / STEP_TEMPLATES_NE / DEFAULT_STEP_TEMPLATE_NE / SEED_STEPS_NE)
- [x] **Bilingual Backend**: 6 new columns (`title_ne`, `category_ne`, `description_ne`, `guidance_ne`, `step_name_ne`, `step_description_ne`) migrated; seed merges NE fields (with step upsert for existing UserServices); all user-facing endpoints accept `lang`; dashboard recommendation scoring made language-independent via English-title map
- [x] **Android Locale Switching**: `LocaleManager` (SharedPreferences) + `EasyGovApp` Application (applies stored locale on launch) + Retrofit lang interceptor; `values-ne/strings.xml` full translation; Profile language selector (`MaterialButtonToggleGroup`) switches app-wide via `AppCompatDelegate.setApplicationLocales`; all layouts/kotlin files converted to `@string` resources; APK rebuilt and verified on emulator (UI + API content + persistence across restart)
- [x] **Document Vault (Backend)**: `POST/GET /api/v1/documents`, `GET /api/v1/documents/{id}/download`, `DELETE /api/v1/documents/{id}`; `documents` table + `documents/{user_id}/` file storage (JPEG/PNG/WEBP/HEIC/PDF, max 10 MB); upload accepts `label`, `tags`, optional `description`; label required/validated; ownership enforced
- [x] **Document Vault (Android)**: New "Documents" bottom-nav tab; `DocumentsFragment` + `DocumentsAdapter` — upload via system picker → label/tags/description dialog → multipart upload; list shows label/filename/tags/size·date; detail sheet (View image preview / open PDF via FileProvider, Delete with confirm); persists across restarts; APK rebuilt and verified end-to-end on emulator (upload → DB+file → list → view → delete → re-upload)
- [x] **Find Nearest Office (Backend)**: `GovernmentOffice` model + migration; `app/geo.py` (haversine + radius filtering/sorting); `GET /api/v1/offices/nearby` router; `office_seed_data.py` seeds 34 real Nepali offices (DAOs, passport/NID centers, DOTM, municipalities) with Devanagari `name_ne`; seed upserts by name; 25 pytest tests pass (distance math, filtering, radius, case-insensitivity, API validation/empty/inactive)
- [x] **Find Nearest Office (Android)**: "Find Nearest Office" button on the service detail screen opens `NearbyOfficesFragment`; requests coarse location on demand only (no background tracking) with permission-denied (incl. permanent → app settings) and location-unavailable states; calls `/api/v1/offices/nearby` (null auth token → no header when signed out) and lists offices sorted nearest-first with distance; each card has a **Directions** button that launches Google Maps turn-by-turn navigation; EN + NE strings; 3 Espresso tests (button visible, button→nearby-screen flow, nearby header) pass on the emulator (Espresso upgraded 3.5.1→3.7.0 + test stack for Android 15+/17 support; host-activity pattern replaced fragment-testing due to its androidx.test:core 1.5.0 pin)
- [x] **Google Sign-In (Backend)**: `app/google_auth.py` — `POST /auth/google` verifies the Android ID token's signature + audience with the official `google-auth` library (`GOOGLE_OAUTH_WEB_CLIENT_ID` env, returns 401 if unconfigured), rejects unverified emails, auto-creates the account (random-secret bcrypt `password_hash` keeps the NOT-NULL column safe), links a first-time Google sign-in to an existing same-email password account, returns the standard JWT `TokenResponse`; `users.google_id` column (nullable, unique) added + migrated; 8 pytest tests (create, link-by-email, match-by-google_id, unconfigured/invalid/unverified-email 401s, deactivated 403, missing field 422) — full suite now **33 passed**
- [x] **Google Sign-In (Android)**: `play-services-auth` added; "Continue with Google" outlined button + OR divider on `fragment_login.xml` (EN + NE strings); `LoginFragment` builds a `GoogleSignInOptions` from the `default_web_client_id` placeholder (tapping while it's the `YOUR_...` placeholder shows a "not set up yet" toast instead of launching), signs out then launches the account chooser, sends the returned ID token to `/auth/google`, and reuses one shared `onAuthSuccess` for token save + dashboard navigation; APK rebuilt (8.1 MB) and verified on the emulator (button renders in both locales, tap fires the placeholder-guard toast, live endpoint returns the intended 401 "not configured")
- [x] **Concise Chatbot + Guide Deep-Link (Android)**: `ChatResponse` gains `guideLink`/`guideServiceId`; `ChatFragment` renders a "View full guide" chip (`chat_view_guide` string, EN + NE) under the assistant reply via a Markwon link (`easygov://guide/<serviceId>`) intercepted by a `LinkResolver` plugin → reuses the Dashboard's `ServiceDetailFragment` (no new screen); `ServiceDetailFragment` now refreshes its title/category header from the fetched (localized) detail so deep-linked guides show the real name; APK rebuilt and verified end-to-end on the emulator — NID question → 3-sentence answer + chip → tap → full NID guide opens; all 4 Espresso tests still pass
- [x] **Concise Chatbot + Guide Deep-Link (Backend)**: `app/ask_utils.py` — new EN + NE system prompts (2–4 sentence answers, strict JSON shape `{answer, topic, suggest_guide}`, JSON keys stay English in the Nepali prompt); `parse_ask_json` (tolerant of code fences / malformed JSON → falls back to raw text); `build_ask_response` maps topic → `guide_link` (`GUIDE_ROUTES`) and `resolve_guide_service` looks up the real `gov_services` row (important: DB ids are NOT sequential — driving_license is id 7) → returns `guide_service_id`; `/ask` now has `response_model=AskResponse` with `guide_link`/`guide_service_id`; chat history stores only the answer text, never the raw JSON; 12 new pytest tests → suite at **45 passed**. Debugged a subtle bug: using `str.format()` on the prompt exploded on the JSON template's braces (`KeyError: '"answer"'`) — switched to `.replace()`; verified live (EN + NE + non-guide question) |

---

## What Is Pending

### Medium Priority - Backend DB Progress Endpoints
- [ ] Resubmit/retry flow for `REJECTED` applications
- [ ] Edit profile endpoint (`PATCH /auth/me`) so users can update phone/address/DOB from the app

### Google Sign-In — fill in real credentials (scaffold shipped with placeholders)
- [ ] Register an OAuth client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — an **Android** client (`com.example.easygov`, with the release/debug SHA-1 from the signing keystore) plus a **Web** client (for the server-side audience check); the Web client ID goes into `default_web_client_id` in `Easygov_mobile/app/src/main/res/values/strings.xml` and into `GOOGLE_OAUTH_WEB_CLIENT_ID` in the backend `.env`
- [ ] Add a Google account to the emulator (Settings → Accounts) and re-run the end-to-end flow
- [ ] (Optional) Migrate `LoginFragment` off the deprecated `GoogleSignIn` API to Credential Manager / Google Identity Services

### Medium Priority - Android UI
- [ ] "My Applications" section on the **dashboard** (currently on Profile screen) so started applications are visible without switching tabs
- [ ] Dashboard service cards show a small status badge (IN PROGRESS / COMPLETED) using the service detail application info
- [ ] Confirmation UI / receipt reference after an application completes

### Low Priority - Nepali Content
- [ ] Re-translate NID guidance headings that remained English (STEP-BY-STEP PROCEDURE / FEES / PROCESSING TIME / OFFICIAL RESOURCES) — cosmetic

---

## Session Log

| Date | What was done |
|---|---|
| 2026-08-05 | Explored full project structure, understood all existing code |
| 2026-08-05 | Designed and implemented full SQL database layer (5 tables) |
| 2026-08-05 | Wrote `migrate.py` and `seed_data.py`, ran both successfully |
| 2026-08-05 | Verified DB: 1 user, 6 services, 4 rules, 2 user_services, 5 progress steps |
| 2026-08-05 | Created `PROGRESS.md` living document |
| 2026-08-05 | Built `/auth/register`, `/auth/login`, `/auth/me` endpoints in FastAPI |
| 2026-08-05 | Wired `LoginFragment` and `DashboardFragment` on Android to real auth API and `SessionManager` |
| 2026-08-07 | Built `/chat/history` endpoint (persists user + assistant messages in `chat_messages`) |
| 2026-08-07 | Added `RegisterFragment`, `ProfileFragment`, chat history bottom sheet + adapter on Android |
| 2026-08-07 | Reviewed full codebase, synced `PROGRESS.md` to reflect actual state |
| 2026-08-08 | Added `age` + `onboarding_completed` to `User`, migrated existing DB, seeded Birth→Citizenship rule |
| 2026-08-08 | Built onboarding + prerequisite-blocking backend (`POST /api/v1/onboarding`, `GET /api/v1/services/{id}`, updated dashboard), verified end-to-end |
| 2026-08-08 | Android: `OnboardingFragment`, next-step banner, blocked-service read-only flow; built APK successfully |
| 2026-08-10 | Added `guidance` column to `gov_services`; rewrote seed with real content from Nepal Essential Documents Guide for Citizenship, NID, E-Passport, and new Driving License service |
| 2026-08-10 | Rebuilt prerequisite rules + `NEXT_STEP_CHAIN` to guide's chain (Citizenship → NID → Passport / Driving License); deactivated Bluebook/Business/Birth |
| 2026-08-10 | Android: service detail now renders full official guide; onboarding checklist updated to the 4 documents; APK rebuilt |
| 2026-08-11 | **Application progress tracking**: backend `/apply`, `/applications/{id}`, `/applications/{id}/steps/{n}/complete` + `STEP_TEMPLATES` for all 4 services; verified end-to-end (blocked apply → 400, apply → steps, complete → advances → auto-complete) |
| 2026-08-11 | Android: `ApplicationModels.kt`, `ApplicationProgressFragment` + layout + `ProgressStepAdapter`, wired Apply Now on service detail; APK built successfully |
| 2026-08-11 | Rich profile: `/auth/me` extended (age, DOB, address, onboarding), new `GET /api/v1/applications`; seed backfills profile for existing test user |
| 2026-08-11 | Android: rewrote `ProfileFragment` + layout — full personal info panel + "My Applications & Progress" list (status chips, progress bars, tap-to-open tracker); APK built successfully |
| 2026-08-13 | **Nepali localization — content**: wrote + ran `app/translate_seed.py` → `app/nepali_content.py` (verified Devanagari service titles/categories/descriptions/guidance, all 4 step templates, default template, seed steps; guidance URLs intact) |
| 2026-08-13 | **Nepali localization — backend**: migrated 6 NE columns; `seed_data.py` merges NE fields + upserts NE steps for existing UserServices; all user-facing endpoints accept `lang=en|ne`; recommendation scoring fixed via English-title map; verified `?lang=ne` returns Devanagari end-to-end, `?lang=en` unaffected |
| 2026-08-13 | **Nepali localization — Android**: `LocaleManager`, `EasyGovApp`, Retrofit lang interceptor, full `values-ne/strings.xml`, Profile language selector, all layouts + Kotlin converted to `@string`; fixed `continue` reserved-word + OkHttp `url()` access build errors; APK rebuilt (7.2 MB) |
| 2026-08-13 | Verified on emulator (Medium_Phone AVD): Profile → नेपाली switches UI + API content to Devanagari (dashboard titles, full service guidance, application titles/status), survives app restart; English toggle unaffected |
| 2026-08-13 | **RAG Nepali query support (Route A)**: `/ask` now detects query language via `langdetect` and answers in the query's language (`NEPALI`/`ENGLISH`); multilingual embeddings already handle cross-lingual retrieval. Verified: Nepali query → Devanagari answer with correct sources; English query unaffected |
| 2026-08-16 | **Document vault**: backend endpoints + `documents` table + per-user file storage; Android `DocumentsFragment`/`DocumentsAdapter` + Documents nav tab + upload/view/delete UI; APK built (7.4 MB) |
| 2026-08-16 | Verified document vault end-to-end on emulator: upload via picker → dialog (label/tags/desc) → stored in `db_storage/documents/{user_id}/` + `easygov.db`; list, detail sheet, image view, delete-with-confirm all work; survives restart |
| 2026-08-16 | **Bugfix**: upload dialog's optional Description field was never read or sent — added `etDocDescription` wiring + `@Part("description")` in `ApiService.uploadDocument`; rebuilt, re-verified description now persists and displays |
| 2026-08-17 | **Find Nearest Office — backend**: `GovernmentOffice` model + migration; `app/geo.py` haversine; `app/offices.py` router (`GET /api/v1/offices/nearby`, radius 1–100 km); `app/office_seed_data.py` (34 real offices); seeding wired into `seed_data.py`; pytest added (`tests/conftest.py`, `test_geo.py`, `test_offices_api.py`) — 25 tests pass |
| 2026-08-17 | **Find Nearest Office — Android**: `Office.kt`, `ApiService.getNearbyOffices` (nullable auth header), `OfficeAdapter` + `item_office.xml`, `NearbyOfficesFragment` + layout (permission/location/empty/error states, single-fix + 15s timeout, Directions → `google.navigation:` intent with `geo:` fallback), button on `fragment_service_detail.xml` + `ServiceDetailFragment` handler with service-title→tag mapping; `ACCESS_COARSE_LOCATION` permission; EN + NE strings; APK rebuilt |
| 2026-08-17 | Verified Find Nearest Office end-to-end on emulator (Medium_Phone, Android 17): service detail → tap "Find Nearest Office" → approximate-location permission dialog → "While using the app" → list of nearby DAOs/municipal offices sorted by distance (0.7/1.7/2.2 km…) → Directions launches Google Maps navigation. Debugged `adb emu geo fix` arg order (takes longitude FIRST — wrong order put the "location" in the Arctic → empty result) |
| 2026-08-17 | **Espresso tests for the flow**: upgraded test stack for Android 15/17 (Espresso 3.5.1→3.7.0, ext-junit 1.1.5→1.3.0, rules/runner/core →1.7.0) — old Espresso crashed with `NoSuchMethodException: InputManager.getInstance`; replaced `fragment-testing` (pins androidx.test:core 1.5.0) with a debug-source-set `FragmentTestHostActivity` + `ActivityScenario`; `NearbyOfficesTest` (3 tests: button shown, tap→nearby screen, nearby header) all pass on device |
| 2026-08-18 | **Google Sign-In — backend**: `app/google_auth.py` router + `google-auth` dependency; `users.google_id` column added + migrated; `POST /auth/google` verifies ID token (audience `GOOGLE_OAUTH_WEB_CLIENT_ID`), auto-creates/links users, returns JWT `TokenResponse`; 8 new pytest tests → suite at 33 passed |
| 2026-08-18 | **Google Sign-In — Android**: `play-services-auth` + "Continue with Google" button (outlined, with OR divider) on login; `LoginFragment` launches account chooser and POSTs the ID token to `/auth/google`; placeholder `default_web_client_id` guard shows a setup toast; shared `onAuthSuccess` with password login; APK rebuilt (8.1 MB); verified on emulator — button renders (EN + NE), tap fires the guard toast (dumpsys window shows the Toast window), live endpoint returns 401 "not configured" until real client IDs are added |
| 2026-08-19 | **Concise chatbot + guide deep-link — backend**: `app/ask_utils.py` with new EN + NE system prompts (2–4 sentence answers, strict JSON `{answer, topic, suggest_guide}`), tolerant `parse_ask_json`, `build_ask_response` maps topic → `guide_link` + `guide_service_id` (real `gov_services` row — driving_license is id 7, not sequential); `/ask` typed as `AskResponse`; chat history stores answer text only; debugged `str.format()` brace explosion → `.replace()`; 12 new pytest tests → **45 passed**; verified live (EN + NE + non-guide question) |
| 2026-08-19 | **Concise chatbot + guide deep-link — Android**: `ChatResponse.guideLink`/`guideServiceId`; "View full guide" chip rendered as a Markwon link (`easygov://guide/<id>`) with a `LinkResolver` plugin → reuses `ServiceDetailFragment` (title/category now refreshed from fetched localized detail); APK rebuilt; verified end-to-end on emulator — "How do I create an NID?" → 3-sentence answer + chip → tap → full NID guide opens; all 4 Espresso tests still pass |
| 2026-08-19 | **Configurable server address (Android)**: `RetrofitClient` base URL is no longer a compile-time constant — stored in SharedPreferences (default `http://10.0.2.2:8000/` for the emulator), `apiService` getter rebuilds the Retrofit instance whenever the URL changes; shared `ServerUrlDialog` (MaterialAlertDialog with prefilled EditText, Save/Cancel, toast on save) opened from a new "Server address" panel on the **Profile** screen and a "Change server address" link on the **Login** screen (so the URL can be fixed even before/during sign-in); EN + NE strings; APK rebuilt and verified on emulator — Profile panel shows current URL, dialog prefills, edit→Save updates the label live, survives force-stop/relaunch, and a real API call through the LAN IP `http://192.168.1.72:8000/` loads profile + applications |
| 2026-08-19 | **Phone connectivity fix (Windows)**: root cause was the hardcoded emulator-only `10.0.2.2` base URL + Windows Firewall blocking inbound on port 8000 (Wi-Fi profile was Public). Added inbound rule `EasyGov_Backend_8000` (TCP 8000, elevation via UAC). With app pointed at the PC's LAN IP, a real phone on the same Wi-Fi can now reach the backend |
| 2026-08-19 | **Physical phone brought online**: phone `dcb8fc4d` (Xiaomi-class, blocks shell tap injection) attached via USB debugging on SSID `prasheshkc_2` (192.168.1.66, same /24 as PC's `prasheshkc_5` 192.168.1.72). Backend had silently died → restarted with `--host 0.0.0.0`; LAN-IP curl from the phone returns 200 (ping is ICMP-blocked by Windows, not a real issue). Rebuilt APK (debug builds land in `app\build\intermediates\apk\debug` + are test-only on this device → install `-r -t`), installed on the phone, and wrote `base_url=http://192.168.1.72:8000/` directly into `easygov_server_prefs.xml` via `run-as`. Session persisted → app is ready against the LAN backend |
