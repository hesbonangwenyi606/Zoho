import requests
import time
import os
import shutil
from datetime import datetime
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

# --- ZOHO CREDENTIALS ---
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")
APP_NAME = os.getenv("ZOHO_APP_NAME")

# --- CONFIGURATION ---
WATCH_FOLDER = r"C:\ZKLogs" 
LOG_FILE_NAME = "attlog.dat" 
PROCESSED_FOLDER = r"C:\ZKLogs\processed"
DEVICE_ID = "ZK9500_DESKTOP_READER"

# Session storage to prevent duplicate uploads if file isn't moved
last_sync_timestamps = {}

def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    try:
        r = requests.post(url, params=params)
        r.raise_for_status() 
        token_data = r.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def push_to_zoho(token, zk_log_data):
    # Updated URL to match specified payload format
    url = f"https://creator.zoho.com/api/v2/{APP_OWNER}/{APP_NAME}/form/Raw_Attendance_Logs/record"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}", 
        "Content-Type": "application/json"
    }
    
    # Format: YYYY-MM-DDTHH:MM:SS
    formatted_time = zk_log_data['timestamp'].strftime("%Y-%m-%dT%H:%M:%S")
    
    # Unique ID based on User + Time to prevent duplicates
    log_id = f"{zk_log_data['user_id']}_{formatted_time}"
    if log_id in last_sync_timestamps:
        return True # Already synced

    payload = {
        "data": {
            "ZKTeco_User_ID": str(zk_log_data['user_id']),
            "Timestamp": formatted_time,
            "Event_Type": zk_log_data['event'],
            "Device_ID": DEVICE_ID
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"✅ Synced: User {zk_log_data['user_id']} at {formatted_time}")
        last_sync_timestamps[log_id] = True
        return True
    except Exception as e:
        print(f"Zoho API Error: {response.text if 'response' in locals() else e}")
        return False

def parse_line(line):
    line = line.strip()
    if not line: return None
    # ZK logs are space/tab separated: UserID YYYY-MM-DD HH:MM:SS 0 1
    parts = line.split() 
    if len(parts) < 3: return None
    try:
        user_id = parts[0]
        # Parse timestamp
        timestamp_dt = datetime.strptime(f"{parts[1]} {parts[2]}", "%Y-%m-%d %H:%M:%S")
        
        # Determine IN/OUT based on ZK status code (usually 0=in, 1=out)
        event = "IN" if (len(parts) > 3 and parts[3] == "0") else "OUT"
        
        return {"user_id": user_id, "timestamp": timestamp_dt, "event": event}
    except Exception as e:
        print(f"Parsing Error on line '{line}': {e}")
        return None

def process_logs():
    file_path = os.path.join(WATCH_FOLDER, LOG_FILE_NAME)
    
    if not os.path.exists(file_path):
        print(f"🔍 Watching: {WATCH_FOLDER} ... (Waiting for {LOG_FILE_NAME})")
        return

    print(f" Found log file! Processing...")
    
    token = get_access_token()
    if not token: 
        print("Could not get access token. Skipping cycle.")
        return

    success_count = 0
    fail_count = 0
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if lines:
            for line in lines:
                data = parse_line(line)
                if data:
                    if push_to_zoho(token, data):
                        success_count += 1
                    else:
                        fail_count += 1

        print(f"📊 Summary: {success_count} succeeded, {fail_count} failed.")

        # Only move file if everything was processed successfully
        if fail_count == 0 and success_count > 0:
            if not os.path.exists(PROCESSED_FOLDER):
                os.makedirs(PROCESSED_FOLDER)
                
            dest = os.path.join(PROCESSED_FOLDER, f"synced_{int(time.time())}.dat")
            shutil.move(file_path, dest)
            print(f"📁 Moved processed file to: {dest}")
        elif success_count == 0 and fail_count == 0:
            print("⚠️ File was empty.")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    print("========================================")
    print("   WINDOWS MIDDLEWARE ACTIVE (10R/9500) ")
    print("========================================")
    while True:
        process_logs()
        time.sleep(60) # Scan every 1 minute