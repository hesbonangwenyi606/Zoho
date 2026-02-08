# Zoho Middleware (ZKTeco + Zoho Creator)

## Purpose
This project connects a **ZKTeco ZK9500** fingerprint reader to **Zoho Creator**
and posts attendance logs into the Zoho app.

Current state:
- Fingerprint capture works (intermittent CAPTURE_FAIL is normal for this SDK).
- Enrollment works (templates saved in `fingerprints.json`).
- Zoho API posting is **still failing** with:
  - `Invalid API URL format` (HTTP 404)
  - This means the API base URL or form/report link names are still wrong.

We need a collaborator to finish the Zoho API URL/form mapping so raw logs post successfully.

## Required .env
```
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
ZOHO_APP_OWNER=...
ZOHO_APP_NAME=...
ZOHO_API_BASE=https://www.zohoapis.com
ZOHO_API_PREFIX=creator/v2

# Optional overrides
ZOHO_DOMAIN=zoho.com
WORKERS_FORM=Workers
RAW_LOGS_FORM=Raw_Attendance_Logs_Form
DEVICES_FORM=Devices
DAILY_ATTENDANCE_FORM=Daily_Attendance

WORKERS_REPORT=All_Workers
RAW_LOGS_REPORT=Raw_Attendance_Logs_Form_Report
DEVICES_REPORT=All_Devices
DAILY_ATTENDANCE_REPORT=Daily_Attendance_Report

DUPLICATE_WINDOW_SECS=3600
PRESENT_FLAG_VALUE=Yes
PENDING_LOGS_FILE=pending_logs.jsonl

# Log file ingestion
ZK_LOGS_FOLDER=C:\ZKLogs
ZK_LOG_FILE=attlog.dat
ZK_PROCESSED_FOLDER=C:\ZKLogs\processed
ZK_DEVICE_ID=ZK9500_DESKTOP_READER

# Fingerprint SDK
ZKFP_DLL_PATH=C:\Windows\SysWOW64\libzkfp.dll
RAW_LOGS_ONLY=1
```

## Run
- Log file ingestion (attlog): `venv\Scripts\python get_refresh_token.py`
- Fingerprint SDK ingestion: `venv32\Scripts\python middleware_fingerprint.py`

## Fingerprint enrollment
Use the CLI:
```
venv32\Scripts\python middleware_fingerprint.py enroll --user-id 10
```
Templates are stored in `fingerprints.json` (override with `FINGERPRINT_DB_FILE`).

## DLL path
Place `zkfp.dll` (or `libzkfp.dll`) in the project root or set:
```
set ZKFP_DLL_PATH=C:\path\to\zkfp.dll
```

## Current blocker (for collaborator)
Raw logs are not posting to Zoho. Error:
```
Raw log add failed: 404 {"code":1000,"description":"Invalid API URL format."}
```

### What to verify
1. **Correct API base**
   - From token response we used: `https://www.zohoapis.com`
   - Path should be: `/creator/v2/{owner}/{app}/...`
2. **Correct form link names**
   - Raw logs form link name might be different than `Raw_Attendance_Logs_Form`
3. **Correct report link names**
   - Report link names might not match defaults

### Suggested debug steps
1. Run `test_zoho.py` with the same venv that runs the middleware:
   ```
   venv32\Scripts\python test_zoho.py
   ```
   If any report call fails, update `.env` report names.
2. If report calls succeed, but form add fails, then **form link name is wrong**.
3. Try both add URLs:
   - `/creator/v2/{owner}/{app}/form/{form}/record`
   - `/creator/v2/{owner}/{app}/form/{form}/record/add`

### Current raw-logs-only mode
`RAW_LOGS_ONLY=1` is set to bypass Daily_Attendance and Worker lookups.
This isolates the problem to **raw log POST only**.

If you fix the API URL/form mapping, set:
```
RAW_LOGS_ONLY=0
```
and Daily Attendance will resume.
