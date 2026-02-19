import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from pyzkfp import ZKFP2
import argparse

# ==============================
# 1. CONFIGURATION
# ==============================
load_dotenv()

ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")
APP_NAME = os.getenv("APP_NAME")
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

ATTENDANCE_FORM = "Daily_Attendance"  # Exact Zoho form link name
ZOHO_BASE = f"https://www.zohoapis.{ZOHO_DOMAIN}/creator/v2"
TOKEN_CACHE = {"token": None, "expires_at": 0}

FINGERPRINT_FILE = "fingerprints.json"


# ==============================
# 2. ZOHO AUTHENTICATION
# ==============================
def get_access_token():
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return TOKEN_CACHE["token"]

    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
    }

    try:
        r = requests.post(url, data=data, timeout=20)
        res = r.json()
        if "access_token" not in res:
            print(" Failed to get access token:", res)
            return None
        TOKEN_CACHE["token"] = res.get("access_token")
        TOKEN_CACHE["expires_at"] = now + int(res.get("expires_in", 3600))
        return TOKEN_CACHE["token"]
    except Exception as e:
        print(" Token request error:", e)
        return None


# ==============================
# 3. LOG ATTENDANCE TO ZOHO
# ==============================
def sync_to_zoho(user_id, worker_name):
    token = get_access_token()
    if not token:
        print("Zoho token refresh failed.")
        return

    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_time_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    try:
        # Check if record exists today
        params = {"criteria": f'(ZKTeco_User_ID2=={user_id}) && (Date=="{today_str}")'}
        r = requests.get(f"{ZOHO_BASE}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_FORM}", headers=headers, params=params)
        records = r.json().get("data", [])

        if records:
            # Update Last Out and Total Hours
            record_id = records[0].get("ID")
            first_in_str = records[0].get("First_In") or current_time_str
            first_in_dt = datetime.strptime(first_in_str, "%Y-%m-%dT%H:%M:%S")
            last_out_dt = datetime.now()
            total_hours = round((last_out_dt - first_in_dt).total_seconds() / 3600, 2)

            update_payload = {
                "data": {
                    "Last_Out": current_time_str,
                    "Total_Hours": total_hours
                }
            }
            update_r = requests.put(f"{ZOHO_BASE}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}/{record_id}", headers=headers, json=update_payload)
            if update_r.status_code in [200, 201]:
                print(f"🕒 Updated {worker_name}: Last Out {current_time_str}, Total Hours {total_hours}h")
            else:
                print("⚠️ Failed to update record:", update_r.text)
        else:
            # Create new record
            payload = {
                "data": {
                    "ZKTeco_User_ID2": str(user_id),
                    "Worker_Name": worker_name,
                    "First_In": current_time_str,
                    "Date": today_str
                }
            }
            log_r = requests.post(f"{ZOHO_BASE}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}", headers=headers, json=payload)
            if log_r.status_code in [200, 201]:
                print(f"✅ Logged First In for {worker_name} at {current_time_str}")
            else:
                print("⚠️ Failed to log attendance:", log_r.text)

    except Exception as e:
        print("API Exception:", e)


# ==============================
# 4. LOAD FINGERPRINT DATA
# ==============================
def load_fingerprints():
    if not os.path.exists(FINGERPRINT_FILE):
        print(f"{FINGERPRINT_FILE} not found.")
        return []
    with open(FINGERPRINT_FILE, "r") as f:
        raw = json.load(f)
        return raw.get("data", raw) if isinstance(raw, dict) else raw


# ==============================
# 5. LIVE FINGERPRINT SENSOR LOOP
# ==============================
def run_live_sensor():
    zkfp2 = ZKFP2()
    zkfp2.Init()

    if zkfp2.GetDeviceCount() == 0:
        print("Fingerprint sensor not found. Reconnect USB.")
        return

    zkfp2.OpenDevice(0)
    print("✅ Fingerprint reader ready")

    items = load_fingerprints()
    if not items:
        return

    for item in items:
        uid = item.get("Worker_ID") or item.get("id")
        blob = item.get("Biometric_Fingerprint")
        if uid and blob:
            zkfp2.DBAdd(int(uid), str(blob))
    print(f"✅ Loaded {len(items)} fingerprints")

    print("\nPlace finger on reader to punch in...")

    try:
        while True:
            capture = zkfp2.AcquireFingerprint()
            if capture:
                tmp, img = capture
                matched_id, score = zkfp2.DBIdentify(tmp)
                if matched_id > 0:
                    worker_name = next(
                        (i.get("Worker_Name") for i in items if int(i.get("Worker_ID") or i.get("id")) == matched_id),
                        f"User_{matched_id}"
                    )
                    print(f"🎯 Match! {worker_name} (ID: {matched_id})")
                    sync_to_zoho(matched_id, worker_name)
                    time.sleep(5)
                else:
                    print("🚫 Fingerprint not recognized")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping fingerprint sensor...")
    finally:
        zkfp2.CloseDevice()
        zkfp2.Terminate()


# ==============================
# 6. STARTUP
# ==============================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, help="Test logging without fingerprint")
    args = parser.parse_args()

    items = load_fingerprints()

    if args.user_id:
        # Auto-find worker name from fingerprints.json
        worker_name = next(
            (i.get("Worker_Name") for i in items if int(i.get("Worker_ID") or i.get("id")) == args.user_id),
            f"User_{args.user_id}"
        )
        sync_to_zoho(args.user_id, worker_name)
    else:
        run_live_sensor()
