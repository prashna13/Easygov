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
| Auth | JWT via `python-jose` · direct bcrypt password hashing |
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
│   ├── main.py                 # FastAPI app — /ask, auth, dashboard, onboarding, service detail, application progress endpoints
│   ├── ingest_data.py          # PDF/MD ingestion pipeline → ChromaDB
│   ├── frontend.py             # Streamlit web UI (dev/demo only)
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
        │   ├── LoginFragment.kt         # [DONE] Calls POST /auth/login, saves JWT via SessionManager
        │   ├── RegisterFragment.kt      # [DONE] Calls POST /auth/register, auto-login after signup
        │   ├── ProfileFragment.kt       # [DONE] Full profile from /auth/me + "My Applications & Progress" list
        │   ├── ApplicationsAdapter.kt   # [DONE] Profile application cards (title/status/progress %) → open tracker
        │   ├── ServiceDetailFragment.kt # [DONE] Detail + guide + prereq blocking; Apply Now starts an application
        │   ├── ApplicationProgressFragment.kt # [DONE] Step checklist + progress bar; ticks steps complete
        │   ├── ProgressStepAdapter.kt    # [DONE] Checklist adapter (current step tappable only)
        │   ├── DashboardAdapter.kt
        │   ├── ChatHistoryAdapter.kt    # [DONE] Adapter for chat history bottom sheet
        │   ├── ChatHistoryBottomSheet.kt# [DONE] Fetches /chat/history, newest-first list
        │   ├── SessionManager.kt        # AES256 encrypted token storage
        │   ├── ChatNetworkInterface.kt  # ChatRequest/ChatResponse/ChatHistoryResponse DTOs
        │   ├── model/
        │   │   ├── GovService.kt
        │   │   ├── DashboardResponse.kt
        │   │   ├── OnboardingModels.kt    # [DONE] Onboarding request/response + ServiceDetailResponse (includes application)
        │   │   ├── ApplicationModels.kt   # [DONE] ApplicationProgress + ProgressStep DTOs
        │   │   └── AuthModels.kt        # [DONE] LoginRequest, RegisterRequest, TokenResponse, UserOut
        │   └── network/
        │       ├── ApiService.kt        # [DONE] Endpoints: dashboard, onboarding, services, apply, applications, steps, /ask, /chat/history, /auth/*
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
            └── item_chat_history.xml
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
| POST | `/ask` | LIVE | RAG chatbot — question → ChromaDB → LLM → answer + sources |
| POST | `/auth/register` | LIVE | Creates user, hashes password with bcrypt, returns JWT token |
| POST | `/auth/login` | LIVE | Verifies bcrypt password, returns JWT token + user profile |
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
| PATCH | `/api/v1/user/services/{service_id}/progress/{step_id}` | NOT BUILT | Superseded by `POST /api/v1/applications/{id}/steps/{n}/complete` (build separately if desired) |

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

---

## What Is Pending

### Medium Priority - Backend DB Progress Endpoints
- [ ] Resubmit/retry flow for `REJECTED` applications
- [ ] Edit profile endpoint (`PATCH /auth/me`) so users can update phone/address/DOB from the app

### Medium Priority - Android UI
- [ ] "My Applications" section on the **dashboard** (currently on Profile screen) so started applications are visible without switching tabs
- [ ] Dashboard service cards show a small status badge (IN PROGRESS / COMPLETED) using the service detail application info
- [ ] Confirmation UI / receipt reference after an application completes

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
