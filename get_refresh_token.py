import os
import shutil
import time
from datetime import datetime

from dotenv import load_dotenv

from middleware_core import handle_punch, retry_pending

load_dotenv()

# --- CONFIGURATION ---
WATCH_FOLDER = os.getenv("ZK_LOGS_FOLDER", r"C:\ZKLogs")
LOG_FILE_NAME = os.getenv("ZK_LOG_FILE", "attlog.dat")
PROCESSED_FOLDER = os.getenv("ZK_PROCESSED_FOLDER", r"C:\ZKLogs\processed")
DEVICE_ID = os.getenv("ZK_DEVICE_ID", "ZK9500_DESKTOP_READER")

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
        
        # Raw event code is not used directly. IN/OUT is computed by middleware.
        return {"user_id": user_id, "timestamp": timestamp_dt, "raw": line}
    except Exception as e:
        print(f"Parsing Error on line '{line}': {e}")
        return None

def process_logs():
    file_path = os.path.join(WATCH_FOLDER, LOG_FILE_NAME)
    
    if not os.path.exists(file_path):
        print(f"🔍 Watching: {WATCH_FOLDER} ... (Waiting for {LOG_FILE_NAME})")
        return

    print(f" Found log file! Processing...")
    
    success_count = 0
    fail_count = 0
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if lines:
            for line in lines:
                data = parse_line(line)
                if data:
                    ok, msg = handle_punch(
                        data["user_id"],
                        data["timestamp"],
                        DEVICE_ID,
                        raw_payload=data.get("raw"),
                        source="attlog",
                    )
                    if ok:
                        success_count += 1
                    else:
                        fail_count += 1
                        print(f"Failed: {msg}")

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
        retry_pending()
        time.sleep(60) # Scan every 1 minute
