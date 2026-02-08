import json
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

# --- ZOHO CONFIG ---
ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")
ZOHO_API_BASE = os.getenv("ZOHO_API_BASE", "")
ZOHO_API_PREFIX = os.getenv("ZOHO_API_PREFIX", "api/v2")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")
APP_NAME = os.getenv("ZOHO_APP_NAME")
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

# --- FORM LINK NAMES ---
WORKERS_FORM = os.getenv("WORKERS_FORM", "Workers")
RAW_LOGS_FORM = os.getenv("RAW_LOGS_FORM", "Raw_Attendance_Logs_Form")
DEVICES_FORM = os.getenv("DEVICES_FORM", "Devices")
DAILY_ATTENDANCE_FORM = os.getenv("DAILY_ATTENDANCE_FORM", "Daily_Attendance")

# --- REPORT LINK NAMES (USED FOR SEARCH/LOOKUP) ---
# If your report link names differ, set them in .env.
WORKERS_REPORT = os.getenv("WORKERS_REPORT", "All_Workers")
RAW_LOGS_REPORT = os.getenv("RAW_LOGS_REPORT", "Raw_Attendance_Logs_Form_Report")
DEVICES_REPORT = os.getenv("DEVICES_REPORT", "All_Devices")
DAILY_ATTENDANCE_REPORT = os.getenv("DAILY_ATTENDANCE_REPORT", "Daily_Attendance_Report")

# --- BEHAVIOR SETTINGS ---
DUPLICATE_WINDOW_SECS = int(os.getenv("DUPLICATE_WINDOW_SECS", "3600"))
PRESENT_FLAG_VALUE = os.getenv("PRESENT_FLAG_VALUE", "Yes")

PENDING_LOGS_FILE = os.getenv("PENDING_LOGS_FILE", "pending_logs.jsonl")
RAW_LOGS_ONLY = os.getenv("RAW_LOGS_ONLY", "0") == "1"

TOKEN_CACHE = {"token": None, "expires_at": 0}


def _now_utc():
    return datetime.utcnow()


def _to_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _to_date(dt):
    return dt.strftime("%Y-%m-%d")


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value)
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        pass
    for fmt in ("%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def get_access_token():
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return TOKEN_CACHE["token"]

    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    try:
        r = requests.post(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException:
        return None
    token = data.get("access_token")
    if not token:
        return None

    expires_in = int(data.get("expires_in", 3600))
    TOKEN_CACHE["token"] = token
    TOKEN_CACHE["expires_at"] = now + expires_in
    return token


def _zoho_request(method, path, token, params=None, payload=None, base_override=None, prefix_override=None):
    base = base_override.rstrip("/") if base_override else (ZOHO_API_BASE.rstrip("/") if ZOHO_API_BASE else f"https://creator.{ZOHO_DOMAIN}")
    prefix = prefix_override.strip("/") if prefix_override else ZOHO_API_PREFIX.strip("/")
    url = f"{base}/{prefix}/{APP_OWNER}/{APP_NAME}/{path.lstrip('/')}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    try:
        r = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=payload,
            timeout=30,
        )
        r._request_url = url
        return r
    except requests.exceptions.RequestException as e:
        class _Resp:
            ok = False
            status_code = 0
            text = str(e)

            def json(self):
                return {}

        resp = _Resp()
        resp._request_url = url
        return resp


def _add_record(form_link, data, token):
    payload = {"data": data}
    path = f"form/{form_link}/record"
    r = _zoho_request("POST", path, token, payload=payload)
    # Fallback for older Creator URL pattern
    if not r.ok and r.status_code == 404 and "Invalid API URL format" in r.text:
        path = f"form/{form_link}/record/add"
        r = _zoho_request("POST", path, token, payload=payload)
    # Fallback to creator domain if zohoapis fails
    if not r.ok and r.status_code == 404 and "Invalid API URL format" in r.text:
        creator_base = f"https://creator.{ZOHO_DOMAIN}"
        r = _zoho_request("POST", path, token, payload=payload, base_override=creator_base, prefix_override="api/v2")
    return r


def _update_record(form_link, record_id, data, token):
    payload = {"data": data}
    path = f"form/{form_link}/record/{record_id}"
    r = _zoho_request("PUT", path, token, payload=payload)
    return r


def _get_records(report_link, criteria=None, sort_by=None, sort_order="desc", start=1, limit=1, token=None):
    params = {"from": start, "limit": limit}
    if criteria:
        params["criteria"] = criteria
    path = f"report/{report_link}"
    r = _zoho_request("GET", path, token, params=params)
    return r


def _append_pending(record):
    with open(PENDING_LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load_pending():
    if not os.path.isfile(PENDING_LOGS_FILE):
        return []
    items = []
    with open(PENDING_LOGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _clear_pending():
    if os.path.isfile(PENDING_LOGS_FILE):
        os.remove(PENDING_LOGS_FILE)


def _find_worker(zkteco_user_id, token):
    user_id = str(zkteco_user_id).strip()
    criteria = f'ZKTeco_User_ID == "{user_id}"'
    r = _get_records(WORKERS_REPORT, criteria=criteria, token=token)
    if not r.ok:
        return None, f"Workers lookup failed: {r.status_code} {r.text}"
    data = r.json().get("data", [])
    if data:
        return data[0], None

    # Fallback to Worker_ID
    criteria = f'Worker_ID == "{user_id}"'
    r = _get_records(WORKERS_REPORT, criteria=criteria, token=token)
    if not r.ok:
        return None, f"Workers lookup failed: {r.status_code} {r.text}"
    data = r.json().get("data", [])
    return (data[0] if data else None), None


def _find_device(device_id, token):
    if not device_id:
        return None, None
    criteria = f'Device_Serial == "{device_id}"'
    r = _get_records(DEVICES_REPORT, criteria=criteria, sort_by="Last_Sync_Timestamp", token=token)
    if not r.ok:
        return None, f"Device lookup failed: {r.status_code} {r.text}"
    data = r.json().get("data", [])
    return (data[0] if data else None), None


def _get_last_non_duplicate_log(zkteco_user_id, token):
    criteria = f'ZKTeco_User_ID == "{zkteco_user_id}" && Event_Type != "DUPLICATE"'
    r = _get_records(RAW_LOGS_REPORT, criteria=criteria, sort_by="Timestamp", token=token)
    if not r.ok:
        return None, f"Raw logs lookup failed: {r.status_code} {r.text}"
    data = r.json().get("data", [])
    return (data[0] if data else None), None


def _get_daily_attendance(worker_id, date_str, token):
    criteria = f'Worker_ID == "{worker_id}" && Date == "{date_str}"'
    r = _get_records(DAILY_ATTENDANCE_REPORT, criteria=criteria, sort_by="Date", token=token)
    if not r.ok:
        return None, f"Daily attendance lookup failed: {r.status_code} {r.text}"
    data = r.json().get("data", [])
    return (data[0] if data else None), None


def handle_punch(zkteco_user_id, timestamp, device_id, raw_payload=None, source=None):
    """
    Main entry point for both fingerprint and log-file ingestion.
    zkteco_user_id: string/int from device
    timestamp: datetime
    device_id: device serial or unique ID
    raw_payload: raw data dict/str for audit
    """
    token = get_access_token()
    if not token:
        _append_pending(
            {
                "reason": "no_token",
                "zkteco_user_id": str(zkteco_user_id),
                "timestamp": _to_iso(timestamp),
                "device_id": device_id,
                "raw_payload": raw_payload,
                "source": source,
            }
        )
        return False, "No Zoho token"

    # Raw logs only mode: skip lookups and daily attendance
    if RAW_LOGS_ONLY:
        raw_json = {
            "source": source,
            "raw_payload": raw_payload,
            "duplicate_window_secs": DUPLICATE_WINDOW_SECS,
        }
        log_record = {
            "ZKTeco_User_ID": str(zkteco_user_id),
            "Worker_ID": None,
            "Timestamp": _to_iso(timestamp),
            "Device_ID": device_id,
            "Event_Type": "IN",
            "Raw_JSON": json.dumps(raw_json),
        }
        r = _add_record(RAW_LOGS_FORM, log_record, token)
        if not r.ok:
            _append_pending({"reason": "raw_log_failed", "record": log_record, "error": r.text})
            return False, f"Raw log add failed: {r.status_code} {r.text}"
        return True, "Raw log stored"

    device_record, device_err = _find_device(device_id, token)
    if device_err and not RAW_LOGS_ONLY:
        return False, device_err

    worker_record, worker_err = _find_worker(zkteco_user_id, token)
    if worker_err and not RAW_LOGS_ONLY:
        return False, worker_err

    worker_record_id = None
    worker_display_id = None
    if worker_record:
        worker_record_id = worker_record.get("ID") or worker_record.get("id")
        worker_display_id = worker_record.get("Worker_ID")

    # Determine duplicate
    last_log, last_log_err = _get_last_non_duplicate_log(zkteco_user_id, token)
    if last_log_err:
        return False, last_log_err

    is_duplicate = False
    last_event_type = None
    if last_log and last_log.get("Timestamp"):
        last_ts = _parse_ts(last_log.get("Timestamp"))
        if last_ts:
            delta = abs((timestamp - last_ts).total_seconds())
            if delta <= DUPLICATE_WINDOW_SECS:
                is_duplicate = True
        last_event_type = last_log.get("Event_Type")

    if is_duplicate:
        event_type = "DUPLICATE"
    else:
        if last_event_type == "IN":
            event_type = "OUT"
        else:
            event_type = "IN"

    raw_json = {
        "source": source,
        "raw_payload": raw_payload,
        "duplicate_window_secs": DUPLICATE_WINDOW_SECS,
    }

    # Write raw attendance log (always)
    log_record = {
        "ZKTeco_User_ID": str(zkteco_user_id),
        "Worker_ID": worker_record_id or worker_display_id,
        "Timestamp": _to_iso(timestamp),
        "Device_ID": device_id,
        "Event_Type": event_type,
        "Raw_JSON": json.dumps(raw_json),
    }
    r = _add_record(RAW_LOGS_FORM, log_record, token)
    if not r.ok:
        _append_pending({"reason": "raw_log_failed", "record": log_record, "error": r.text})
        return False, f"Raw log add failed: {r.status_code} {r.text}"

    # Only update Daily_Attendance for non-duplicate events (and when worker exists)
    if event_type == "DUPLICATE":
        return True, "Duplicate stored"
    if RAW_LOGS_ONLY or not worker_record:
        return True, "Raw log stored (no worker)"

    date_str = _to_date(timestamp)
    daily_rec, daily_err = _get_daily_attendance(worker_record_id or worker_display_id, date_str, token)
    if daily_err:
        return False, daily_err

    project_id = None
    if device_record and device_record.get("Project_ID"):
        project_id = device_record.get("Project_ID")

    if not daily_rec:
        create_data = {
            "Worker_ID": worker_record_id or worker_display_id,
            "Projects": project_id,
            "Date": date_str,
            "Present_Flag": PRESENT_FLAG_VALUE,
        }
        if event_type == "IN":
            create_data["First_In"] = _to_iso(timestamp)
        elif event_type == "OUT":
            create_data["Last_Out"] = _to_iso(timestamp)
            create_data["Remarks"] = "OUT without prior IN"

        r = _add_record(DAILY_ATTENDANCE_FORM, create_data, token)
        if not r.ok:
            _append_pending({"reason": "daily_create_failed", "record": create_data, "error": r.text})
            return False, f"Daily attendance create failed: {r.status_code} {r.text}"
    else:
        update_data = {}
        first_in = daily_rec.get("First_In")
        last_out = daily_rec.get("Last_Out")

        if event_type == "IN" and not first_in:
            update_data["First_In"] = _to_iso(timestamp)
        if event_type == "OUT":
            update_data["Last_Out"] = _to_iso(timestamp)

        # Recompute total hours if we have both
        if (first_in or update_data.get("First_In")) and (last_out or update_data.get("Last_Out")):
            fi = update_data.get("First_In", first_in)
            lo = update_data.get("Last_Out", last_out)
            fi_dt = _parse_ts(fi)
            lo_dt = _parse_ts(lo)
            if fi_dt and lo_dt:
                total_hours = round((lo_dt - fi_dt).total_seconds() / 3600, 2)
                update_data["Total_Hours"] = total_hours

        if project_id and not daily_rec.get("Projects"):
            update_data["Projects"] = project_id

        if update_data:
            record_id = daily_rec.get("ID") or daily_rec.get("id")
            if not record_id:
                return False, "Daily attendance record ID missing"
            r = _update_record(DAILY_ATTENDANCE_FORM, record_id, update_data, token)
            if not r.ok:
                _append_pending({"reason": "daily_update_failed", "record": update_data, "error": r.text})
                return False, f"Daily attendance update failed: {r.status_code} {r.text}"

    # Update device sync timestamp (best-effort)
    if device_record:
        record_id = device_record.get("ID") or device_record.get("id")
        if record_id:
            _update_record(
                DEVICES_FORM,
                record_id,
                {"Last_Sync_Timestamp": _to_iso(timestamp)},
                token,
            )

    return True, "Processed"


def retry_pending():
    items = _load_pending()
    if not items:
        return 0, 0
    success = 0
    fail = 0
    token = get_access_token()
    if not token:
        return 0, len(items)
    for item in items:
        reason = item.get("reason")
        if reason in ("no_token", "worker_not_found"):
            ok, _ = handle_punch(
                item.get("zkteco_user_id"),
                datetime.fromisoformat(item.get("timestamp")),
                item.get("device_id"),
                raw_payload=item.get("raw_payload"),
                source=item.get("source"),
            )
        elif reason == "raw_log_failed":
            r = _add_record(RAW_LOGS_FORM, item.get("record"), token)
            ok = r.ok
        else:
            ok = False

        if ok:
            success += 1
        else:
            fail += 1

    if fail == 0:
        _clear_pending()
    return success, fail
