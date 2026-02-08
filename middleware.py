import os
import json
import csv
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")  # wavemarkpropertieslimited
APP_NAME = os.getenv("ZOHO_APP_NAME")    # real-estate-wages-system
FORM_LINK_NAME = "Raw_Attendance_Logs_Form"
ZOHO_DOMAIN = "zoho.com"

# Local CSV to store pending attendance records
CSV_FILE = "attendance_pending.csv"

# --- Helper Functions ---

def get_access_token():
    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    params = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    data = response.json()
    return data.get("access_token")

def push_to_zoho(record, token):
    url = f"https://creator.{ZOHO_DOMAIN}/api/v2/{APP_OWNER}/{APP_NAME}/form/{FORM_LINK_NAME}/record/add"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json"
    }
    payload = {"data": record}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

def save_to_csv(record):
    """Save a record locally if Zoho API is not available yet"""
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=record.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)
    print(f"✅ Saved locally: {record}")

def read_pending_csv():
    """Read pending records from CSV"""
    if not os.path.isfile(CSV_FILE):
        return []
    with open(CSV_FILE, mode="r") as f:
        reader = csv.DictReader(f)
        return list(reader)

def clear_csv():
    """Clear CSV after successful push"""
    if os.path.isfile(CSV_FILE):
        os.remove(CSV_FILE)

# --- Main Middleware Logic ---

def process_zkteco_log(user_id, worker_id, event_type, device_id):
    timestamp = datetime.now().isoformat(timespec="seconds")
    record = {
        "ZKTeco_User_ID": user_id,
        "Worker_ID": worker_id,
        "Timestamp": timestamp,
        "Event_Type": event_type,
        "Device_ID": device_id,
        "Raw_JSON": json.dumps({"simulated":"data"})
    }

    token = get_access_token()
    if token:
        status, resp = push_to_zoho(record, token)
        if status in [200, 201]:
            print(f"✅ Pushed to Zoho: {record}")
        else:
            print(f"⚠️ Zoho push failed, saving locally. Status: {status}")
            save_to_csv(record)
    else:
        print("⚠️ Could not get Zoho token, saving locally.")
        save_to_csv(record)

# --- Push pending records once token is available ---
def push_pending_records():
    pending = read_pending_csv()
    if not pending:
        return
    print(f"🔄 Pushing {len(pending)} pending records to Zoho...")
    token = get_access_token()
    if not token:
        print("⚠️ Cannot push pending records, token not available.")
        return
    for record in pending:
        status, resp = push_to_zoho(record, token)
        if status in [200, 201]:
            print(f"✅ Pushed pending record: {record}")
        else:
            print(f"⚠️ Failed to push pending record: {record} | Status: {status}")
    clear_csv()

# --- Simulation of ZKTeco logs ---
if __name__ == "__main__":
    print("=== ZKTeco Middleware Simulator ===")

    # Example: simulate a few scans
    process_zkteco_log("1001", "W001", "IN", "ZKTeco_9500_10R")
    time.sleep(1)
    process_zkteco_log("1002", "W002", "OUT", "ZKTeco_9500_10R")

    # Try pushing pending records
    push_pending_records()
