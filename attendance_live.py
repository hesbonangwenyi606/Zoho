import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from pyzkfp import ZKFP2

load_dotenv()

ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER = os.getenv("APP_OWNER")
APP_NAME = os.getenv("APP_NAME")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
WORKERS_REPORT = os.getenv("WORKERS_REPORT", "All_Workers")
RAW_LOGS_FORM = os.getenv("RAW_LOGS_FORM", "Raw_Attendance_Logs_Form")

def get_token():
    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
    return requests.post(url, data=data).json().get("access_token")

def log_attendance(worker_id):
    token = get_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    url = f"https://www.zohoapis.com/creator/v2/{APP_OWNER}/{APP_NAME}/form/{RAW_LOGS_FORM}"
    payload = {"data": {"Worker_ID": str(worker_id), "Timestamp": datetime.now().strftime("%d-%b-%Y %H:%M:%S"), "Event_Type": "IN"}}
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print(f"✅ Attendance recorded for Worker {worker_id}")

def start_live_mode():
    zkfp2 = ZKFP2()
    zkfp2.Init()
    zkfp2.OpenDevice(0)
    print("🔄 Downloading fingerprints from Zoho...")
    
    token = get_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    report_url = f"https://www.zohoapis.com/creator/v2/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    workers = requests.get(report_url, headers=headers).json().get("data", [])
    
    user_map = {}
    for w in workers:
        template = w.get("Fingerprint_Template")
        user_id = w.get("ZKTeco_User_ID")
        if template and user_id:
            internal_id = int(user_id) % 1000
            zkfp2.DBAdd(internal_id, bytes.fromhex(template))
            user_map[internal_id] = user_id
    
    print(f"🟢 Scanner Ready! Loaded {len(user_map)} users. Start scanning...")

    try:
        while True:
            capture = zkfp2.AcquireFingerprint()
            if capture:
                tmp_bytes = bytes(list(capture[0]))
                matched_id, score = zkfp2.DBIdentify(tmp_bytes)
                if matched_id > 0:
                    worker_id = user_map.get(matched_id)
                    print(f"🎯 Matched Worker: {worker_id}")
                    log_attendance(worker_id)
                    time.sleep(5)
            time.sleep(0.1)
    finally:
        zkfp2.Terminate()

if __name__ == "__main__":
    start_live_mode()