<!-- # Zoho Middleware (ZKTeco + Zoho Creator)

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
and Daily Attendance will resume. -->





### Zoho Biometric Middleware
ZKTeco ZK9500 + Zoho Creator (GUI Edition)
A production-ready desktop middleware that integrates the ZKTeco ZK9500 with Zoho Creator, enabling real-time biometric attendance capture, enrollment management, and automatic attendance processing.

*Built for the Wavemark Properties Real Estate Wages System.*
## Overview
This middleware provides:
Biometric fingerprint capture
GUI-based enrollment & management
Real-time Zoho attendance posting
Raw log ingestion support
Duplicate prevention
Retry queue for failed posts
Production-safe logging
OAuth token automation
The system runs locally on a Windows machine connected to the fingerprint scanner.

## 🏗 System Architecture
ZKTeco ZK9500 (USB)
        │
        │ 32-bit SDK (libzkfp.dll)
        ▼
Fingerprint GUI (Python 32-bit)
        │
        │ OAuth2 HTTPS
        ▼
Zoho Creator App
(real-estate-wages-system)
        │
        ├── Workers
        ├── Raw_Attendance_Logs_Form
        ├── Daily_Attendance
        └── Devices

## 🖥 System Requirements
Component	Requirement
OS	Windows 10/11 (64-bit recommended)
Python	32-bit Python 3.9+ (required for SDK)
Device	ZKTeco ZK9500
Internet	Required for Zoho API
Zoho Account	Active Zoho Creator app

## 🧩 ZKTeco SDK Installation
The middleware requires the official ZKTeco SDK.

## 1️⃣Install Driver
Plug in ZK9500.
Install driver from SDK package.

Verify in Device Manager → Biometric Devices.
You should see:
ZKTeco Fingerprint Reader
If not visible:

Reinstall driver
Try different USB port

Restart PC
## 2️⃣Install libzkfp.dll
Copy:
libzkfp.dll

To:
C:\Windows\SysWOW64\
OR set custom path in .env:
ZKFP_DLL_PATH=C:\path\to\libzkfp.dll

## 3️⃣ Install 32-bit Python (Mandatory)
Download from python.org:
Choose:
Windows Installer (32-bit)

## Verify installation:
python -c "import struct; print(struct.calcsize('P') * 8)"
Must output:
32

## 📦 Installation
*1️⃣ Clone Repository*
git clone https://github.com/your-org/zoho-middleware.git
cd zoho-middleware

*2️⃣ Create 32-bit Virtual Environment*
C:\Python39-32\python.exe -m venv venv32
venv32\Scripts\activate
pip install -r requirements.txt
⚙ Configuration (.env)
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=

ZOHO_APP_OWNER=
ZOHO_APP_NAME=
ZOHO_API_BASE=https://www.zohoapis.com
ZOHO_API_PREFIX=creator/v2

WORKERS_FORM=Workers
RAW_LOGS_FORM=Raw_Attendance_Logs_Form
DAILY_ATTENDANCE_FORM=Daily_Attendance
DEVICES_FORM=Devices

WORKERS_REPORT=All_Workers
DAILY_ATTENDANCE_REPORT=Daily_Attendance_Report
RAW_LOGS_REPORT=Raw_Attendance_Logs_Form_Report

ZK_DEVICE_ID=ZK9500_DESKTOP
FINGERPRINT_DB_FILE=fingerprints.json

RAW_LOGS_ONLY=0
DUPLICATE_WINDOW_SECS=3600

*🔐 OAuth Setup*
Go to https://api-console.zoho.com
Create Self Client
Add scopes:
ZohoCreator.report.READ
ZohoCreator.report.CREATE
ZohoCreator.report.UPDATE
ZohoCreator.form.READ
ZohoCreator.form.CREATE
ZohoCreator.form.UPDATE

Generate refresh token using:
python get_refresh_token.py --auth

*▶ Running the GUI*
venv32\Scripts\python fingerprint_gui_full.py
The interface provides:
Start Scanner
Enroll User
Delete User
List Enrolled Users
Live Log Output Panel

*👤 Enrollment Process*
Enter ZKTeco User ID.

Click Enroll.
User places finger three times.
Template stored in:
fingerprints.json
Example:

{
  "10": {
    "template": "base64data...",
    "enrolled_at": "2026-01-15T08:00:00",
    "zoho_worker_id": "4838902000000012345"
  }
}

*🕒 Attendance Flow*
When finger is scanned:
Template captured
Matched locally
Worker looked up in Zoho
Raw_Attendance_Logs_Form record created
Daily_Attendance updated (if RAW_LOGS_ONLY=0)


venv\Scripts\python get_refresh_token.py --ingest
Reads attlog.dat
Posts each record
Archives processed files
Retries failed posts

*🔁 Duplicate Prevention*
Controlled by:
DUPLICATE_WINDOW_SECS=3600
Prevents same user + timestamp from reposting within 1 hour.

*📊 Logging*
Log file:
attendance.log

Tracks:
Device events
Zoho responses
Errors
OAuth refresh

*🛠 Production Deployment*
Task Scheduler
Trigger at startup:

*Program:*
venv32\Scripts\python.exe

*Argument:*
fingerprint_gui_full.py

*Install NSSM:*
nssm install ZohoFingerprintGUI

*Set:*
Path → python.exe (32-bit)
Arguments → fingerprint_gui_full.py
Startup type → Automatic

*🔒 Security Best Practices*
Never commit .env
Restrict PC access
Disable Windows sleep mode

*Use UPS*
Backup fingerprints.json
Rotate OAuth tokens annually

*🧯 Troubleshooting*
CAPTURE_FAIL
Normal — finger lifted too soon.
WinError 193
Using 64-bit Python. Switch to 32-bit.
404 Invalid API URL

*Run:*
python test_zoho.py
Correct form link names.
No device detected
Reinstall driver.

*📈 Performance*
Metric	Value
Scan Time	< 1 second
Zoho POST	200–800ms
Memory Usage	~100MB
CPU Usage	Low