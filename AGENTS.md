# Project Working Conventions

## Backend / ports
- Whenever a dev server is started for testing (e.g. `uvicorn app.main:app --port 8000`), **free the port before finishing the task** — kill the leftover process so port 8000 is never left bound.
  - Find it: `Get-NetTCPConnection -LocalPort 8000 -State Listen | Select OwningProcess`
  - Confirm it's uvicorn: `(Get-CimInstance Win32_Process -Filter "ProcessId=<PID>").CommandLine`
  - Kill it: `Stop-Process -Id <PID> -Force`
- Verify the port is free after every task that started a server.

## Physical phone testing
- The phone attaches via USB debugging (`adb devices`: `dcb8fc4d`). The phone must be on the same router subnet as the PC (it may be a different SSID — e.g. PC on `prasheshkc_5`, phone on `prasheshkc_2` — but same `192.168.1.0/24`; verify with `adb shell ip addr show wlan0` and reachability via `adb shell "curl -s -o /dev/null -w '%{http_code}' http://192.168.1.72:8000/"`).
- The backend URL is **baked in at build time** (`BuildConfig.BASE_URL`, from `-Peasygov.baseUrl`). For a physical phone, build with the PC's LAN IP, e.g.:
  - `.\gradlew.bat :app:assembleDebug -x lint -Peasygov.baseUrl=http://192.168.1.72:8000/`
- `RetrofitClient.getBaseUrl()` still honours a SharedPreferences override (`easygov_server_prefs` → `base_url`) as a debug-only fallback, but it is not user-facing (the in-app editor was removed).
- `adb shell input tap` is blocked on this device (`INJECT_EVENTS` SecurityException) unless the OEM "USB debugging (Security settings)" developer option is enabled — you cannot drive the phone UI blindly from here.
- Debug APKs are marked test-only on this device: install with `adb install -r -t`.
- The APK may land at `app\build\intermediates\apk\debug\app-debug.apk` (not `outputs\apk\debug`) — glob for `**/*.apk` if the usual path is missing.

## Admin portal / RAG ingest
- The server must run with `ADMIN_TOKEN` set in `.env`. The `/admin/*` endpoints require header `X-Admin-Token: <ADMIN_TOKEN>`.
- Run the admin UI: `streamlit run app/admin_app.py`, then set the backend address (default `http://127.0.0.1:8000`) and the same `ADMIN_TOKEN` in the sidebar.
- Admin capabilities:
  - **Services & Guidance tab**: edit a service's catalog fields and the guidance shown on the app's guide page. This does **not** touch the RAG/chatbot.
  - **RAG Ingest tab**: upload a PDF/MD into `data_source/<service>/` to update the chatbot's knowledge; supports a version label and "replace previous version" (clears older files for that folder before indexing).
- RAG ingestion reuses the in-process embeddings/vector store and the `SQLRecordManager` (incremental, keyed on `source`), so re-uploading edits a file instead of duplicating it.
