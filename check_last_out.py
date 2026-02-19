import os
import time
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv
from pyzkfp import ZKFP2

# ==========================================================
# 1. CONFIGURATION
# ==========================================================
load_dotenv()

ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER = os.getenv("APP_OWNER")
APP_NAME = os.getenv("APP_NAME")
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

WORKERS_REPORT = "All_Workers"
ATTENDANCE_REPORT = "Daily_Attendance_Report"

TOKEN_CACHE = {"token": None, "expires_at": 0}
API_DOMAIN = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"


# ==========================================================
# 2. AUTHENTICATION
# ==========================================================
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
        response = requests.post(url, data=data, timeout=20)
        result = response.json()

        if "access_token" in result:
            TOKEN_CACHE["token"] = result["access_token"]
            TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
            return TOKEN_CACHE["token"]

    except Exception as e:
        print(f"Authentication Error: {e}")

    return None


# ==========================================================
# 3. FIND WORKER
# ==========================================================
def find_worker(user_id):
    token = get_access_token()
    if not token:
        print("No access token available.")
        return None

    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    criteria = f'(ZKTeco_User_ID2 == {int(user_id)})'

    response = requests.get(report_url, headers=headers, params={"criteria": criteria})
    data = response.json().get("data", [])

    return data[0] if data else None


# ==========================================================
# 4. PROCESS CHECKOUT
# ==========================================================
def process_checkout(worker_record_id, worker_name):
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    now = datetime.now()
    today_str = now.strftime("%d-%b-%Y")

    report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"

    active_record = None

    # Retry to handle Zoho indexing delay
    for _ in range(5):
        response = requests.get(report_url, headers=headers, params={"from": 1, "limit": 20})

        if response.status_code != 200:
            print(f"API Error: {response.text}")
            return

        records = response.json().get("data", [])

        for record in records:
            rec_worker_name = record.get("Worker_Name", "")
            last_out = record.get("Last_Out", "")
            first_in = record.get("First_In", "")

            if today_str in str(first_in) and worker_name in str(rec_worker_name):
                if not last_out or str(last_out).strip().lower() in ["null", ""]:
                    active_record = record
                    break

        if active_record:
            break

        time.sleep(2)

    if not active_record:
        print(f"No open Check-In found for {worker_name} on {today_str}.")
        print("Ensure the worker has checked in first.")
        return

    first_in_val = active_record.get("First_In")

    try:
        first_in_dt = datetime.strptime(first_in_val, "%d-%b-%Y %H:%M:%S")
        duration = now - first_in_dt

        total_hours = round(duration.total_seconds() / 3600, 2)

        h, remainder = divmod(int(duration.total_seconds()), 3600)
        m, s = divmod(remainder, 60)
        total_time_str = f"{h}h {m}m {s}s"

    except Exception as e:
        print(f"Calculation Error: {e}")
        return

    checkout_timestamp = now.strftime("%d-%b-%Y %H:%M:%S")
    checkout_time_only = now.strftime("%H:%M:%S")

    update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}/{active_record['ID']}"
    payload = {
        "data": {
            "Last_Out": checkout_timestamp,
            "Total_Hours": total_hours,
            "Total_Time_Str": total_time_str
        }
    }

    response = requests.patch(update_url, headers=headers, json=payload)

    if response.status_code == 200:
        print(f"{worker_name} checked OUT at {checkout_time_only}")
        print(f"Total Time Worked: {total_time_str}")
        print("Today's Attendance Summary:")
        print(f"First In  : {first_in_val}")
        print(f"Last Out  : {checkout_timestamp}")
        print(f"Total Time: {total_time_str}")
    else:
        print(f"Zoho Update Failed: {response.text}")


# ==========================================================
# 5. FINGERPRINT SENSOR LOGIC
# ==========================================================
def run_checkout_with_sensor(user_id):
    zkfp2 = ZKFP2()
    zkfp2.Init()

    if zkfp2.GetDeviceCount() == 0:
        print("USB fingerprint device not detected.")
        return

    zkfp2.OpenDevice(0)

    print("USB sensor ready.")
    print("Scan finger to checkout.")

    try:
        capture = None

        while not capture:
            capture = zkfp2.AcquireFingerprint()
            time.sleep(0.1)

        worker = find_worker(user_id)

        if worker:
            process_checkout(worker["ID"], worker.get("Full_Name", "Worker"))
        else:
            print(f"Worker ID {user_id} not found.")

    finally:
        zkfp2.CloseDevice()
        zkfp2.Terminate()


# ==========================================================
# 6. ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=str, required=True)
    args = parser.parse_args()

    run_checkout_with_sensor(args.user_id)