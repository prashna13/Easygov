# Project Working Conventions

## Backend / ports
- Whenever a dev server is started for testing (e.g. `uvicorn app.main:app --port 8000`), **free the port before finishing the task** — kill the leftover process so port 8000 is never left bound.
  - Find it: `Get-NetTCPConnection -LocalPort 8000 -State Listen | Select OwningProcess`
  - Confirm it's uvicorn: `(Get-CimInstance Win32_Process -Filter "ProcessId=<PID>").CommandLine`
  - Kill it: `Stop-Process -Id <PID> -Force`
- Verify the port is free after every task that started a server.

## Physical phone testing
- The phone attaches via USB debugging (`adb devices`: `dcb8fc4d`). The phone must be on the same router subnet as the PC (it may be a different SSID — e.g. PC on `prasheshkc_5`, phone on `prasheshkc_2` — but same `192.168.1.0/24`; verify with `adb shell ip addr show wlan0` and reachability via `adb shell "curl -s -o /dev/null -w '%{http_code}' http://192.168.1.72:8000/"`).
- `adb shell input tap` is blocked on this device (`INJECT_EVENTS` SecurityException) unless the OEM "USB debugging (Security settings)" developer option is enabled — you cannot drive the phone UI blindly from here.
- To set the app's backend URL without UI input, write the SharedPreferences directly with `run-as` (debug build):
  - `adb shell am force-stop com.example.easygov`
  - `adb push prefs.xml /data/local/tmp/prefs.xml` where prefs.xml contains `<map><string name="base_url">http://192.168.1.72:8000/</string></map>`
  - `adb shell run-as com.example.easygov cp /data/local/tmp/prefs.xml shared_prefs/easygov_server_prefs.xml`
  - relaunch the app
- Debug APKs are marked test-only on this device: install with `adb install -r -t`.
- The APK may land at `app\build\intermediates\apk\debug\app-debug.apk` (not `outputs\apk\debug`) — glob for `**/*.apk` if the usual path is missing.
