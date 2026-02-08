import requests
import time
from datetime import datetime, timedelta
import os
import shutil

# --- ZOHO CREDENTIALS ---
CLIENT_ID = "1000.X8OHDXTUMT7K4UM7MTERMP1SWNQCPW"
CLIENT_SECRET = "4660b7bca3696132842ac1b2dffd8b7cbf9d3356d0"
REFRESH_TOKEN = "1000.0f68da9642e45f2fb4566b17ea5e1958.268aa1fcef99b5758a78f4ca3110109d"
APP_OWNER = "wavemarkpropertieslimited"
APP_NAME = "real-estate-wages-system"

# --- ZKTECO WSL CONFIGURATION ---
# We use /mnt/d/ because you are running this in Linux (WSL)
ZK_USB_MOUNT_POINT = "/mnt/d/" 
ZK_LOG_FILE_NAME = "attlog.dat" 
ZK_PROCESSED_FOLDER = "processed_logs"

# Storage to prevent duplicate uploads in the same session
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
        r = requests.post(url, params=params).json()
        return r.get("access_token")
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        return None

def push_to_zoho(zk_log_data, device_serial):
    token = get_access_token()
    if not token: return

    url = f"https://creator.zoho.com/api/v2/{APP_OWNER}/{APP_NAME}/form/Raw_Attendance_Logs_Form"
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
    
    payload = {
        "data": {
            "ZKTeco_User_ID": str(zk_log_data['user_id']),
            "Timestamp": zk_log_data['timestamp'].strftime("%d-%b-%Y %H:%M:%S"),
            "Event_Type": zk_log_data['event'],
            "Device_ID": device_serial
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        print(f"✅ Sent: User {zk_log_data['user_id']} at {zk_log_data['timestamp']}")
    else:
        print(f"❌ Zoho Error: {response.text}")

def parse_zk_log_line(line):
    """Parses standard ZKTeco attlog.dat (Space/Tab separated)"""
    line = line.strip()
    if not line: return None

    # ZKTeco logs are usually: UserID  Timestamp  Status  VerifyType
    # Example: 1  2024-02-07 14:10:05  0  1
    parts = line.split() 

    if len(parts) < 3: return None

    try:
        user_id = parts[0]
        # Join date and time parts
        timestamp_str = f"{parts[1]} {parts[2]}" 
        timestamp_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        
        # Determine IN/OUT based on the 4th column if available, else default to IN
        event_code = parts[3] if len(parts) > 3 else "0"
        event_type = "IN" if event_code == "0" else "OUT"

        return {
            "user_id": user_id,
            "timestamp": timestamp_dt,
            "event": event_type
        }
    except Exception as e:
        return None

def process_logs():
    full_path = os.path.join(ZK_USB_MOUNT_POINT, ZK_LOG_FILE_NAME)
    
    if not os.path.exists(full_path):
        print(f"🔍 Searching for {ZK_LOG_FILE_NAME} on {ZK_USB_MOUNT_POINT}...")
        return

    print(f"🚀 Found log file! Processing...")
    
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()

        if not lines:
            print("Empty file.")
        else:
            for line in lines:
                data = parse_zk_log_line(line)
                if data:
                    push_to_zoho(data, "USB_DEVICE_D")

        # Move file so we don't process it twice
        proc_dir = os.path.join(ZK_USB_MOUNT_POINT, ZK_PROCESSED_FOLDER)
        if not os.path.exists(proc_dir): os.makedirs(proc_dir)
        
        dest = os.path.join(proc_dir, f"processed_{int(time.time())}.dat")
        shutil.move(full_path, dest)
        print(f"📁 Moved file to {ZK_PROCESSED_FOLDER}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=== ZKTeco to Zoho Sync (WSL Mode) ===")
    while True:
        process_logs()
        time.sleep(10) # Checks every 10 seconds