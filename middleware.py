import requests
import time
from datetime import datetime, timedelta
import os
import shutil # For moving/deleting files

# --- ZOHO CREDENTIALS --- (Keep these as they are)
CLIENT_ID = "1000.X8OHDXTUMT7K4UM7MTERMP1SWNQCPW"
CLIENT_SECRET = "4660b7bca3696132842ac1b2dffd8b7cbf9d3356d0"
REFRESH_TOKEN = "1000.0f68da9642e45f2fb4566b17ea5e1958.268aa1fcef99b5758a78f4ca3110109d"
APP_OWNER = "wavemarkpropertieslimited"
APP_NAME = "real-estate-wages-system"

# --- ZKTECO USB CONFIGURATION ---
# IMPORTANT: You'll need to determine the mount point for your device
# On Windows, it's typically a drive letter like "D:", "E:", etc.
# On Linux/macOS, it's usually under /media or /Volumes
ZK_USB_MOUNT_POINT = "D:\\" # <<< REPLACE THIS with your device's mount point!
ZK_LOG_FILE_NAME = "attlog.dat" # <<< REPLACE THIS with the actual log file name!
ZK_PROCESSED_FOLDER = "processed_logs" # Folder to move processed logs to

# --- Last Sync Timestamp Storage (For a single device, in memory for this example) ---
# In a real deployment, this would be stored in DynamoDB or a file.
last_sync_timestamps = {} # Key: device_serial, Value: datetime object (used to prevent reprocessing)

# --- Zoho Access Token Function (Keep as is) ---
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
        print(f"Error getting access token: {e}")
        return None

# --- Push to Zoho Function (Modified to accept parsed log dict) ---
def push_to_zoho(zk_log_data, device_serial):
    token = get_access_token()
    if not token:
        print("Auth Failed")
        return

    url = f"https://creator.zoho.com/api/v2/{APP_OWNER}/{APP_NAME}/form/Raw_Attendance_Logs_Form"
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "Content-Type": "application/json"}
    
    payload = {
        "data": {
            "ZKTeco_User_ID": str(zk_log_data['user_id']),
            "Timestamp": zk_log_data['timestamp'].isoformat(),
            "Event_Type": zk_log_data['event'],
            "Device_ID": device_serial,
            "Raw_JSON": str(zk_log_data) # Send the full raw log for auditing
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    res_data = response.json()

    if str(res_data.get("code")) == "3000":
        print(f"\n✅ SUCCESS: Sent User {zk_log_data['user_id']} ({zk_log_data['event']}) from {device_serial} to Zoho.")
    else:
        print(f"\nERROR pushing log: {response.text}")

# --- NEW: ZKTeco Log File Parsing Function ---
def parse_zk_log_line(line):
    """
    Parses a single line from the ZKTeco log file.
    You MUST adapt this function based on the actual format of your log file.
    """
    line = line.strip()
    if not line:
        return None

    # --- EXAMPLE PARSING ---
    # ASSUMPTION: Log line is comma-separated: "USER_ID,TIMESTAMP,EVENT_CODE,DEVICE_ID"
    # e.g., "123,2026-02-03 08:15:22,0,ABC12345"
    # ZKTeco Event Codes often: 0=IN, 1=OUT
    
    parts = line.split(',') # Try splitting by comma. If it's tab, use '\t'. If space, use ' '

    if len(parts) < 4: # Adjust based on how many fields your log file has
        print(f"Skipping malformed line: {line}")
        return None

    try:
        user_id = int(parts[0].strip())
        # Try different timestamp formats if this one fails
        timestamp_str = parts[1].strip()
        timestamp_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S") # Adjust format here!
        
        event_code = int(parts[2].strip()) # Or string if it's "IN"/"OUT"
        event_type = "IN" if event_code == 0 else "OUT" # Adjust based on your device's codes

        device_serial = parts[3].strip()

        return {
            "user_id": user_id,
            "timestamp": timestamp_dt,
            "event": event_type,
            "device_serial": device_serial,
            "raw_line": line # Keep raw line for full fidelity
        }
    except ValueError as e:
        print(f"Error parsing log line '{line}': {e}")
        return None
    except IndexError as e:
        print(f"Index error parsing log line '{line}': {e}")
        return None

# --- NEW: ZKTeco USB Device Interaction Logic ---
def process_zkteco_usb_logs(mount_point, log_file_name):
    global last_sync_timestamps
    
    full_log_path = os.path.join(mount_point, log_file_name)
    processed_dir = os.path.join(mount_point, ZK_PROCESSED_FOLDER)
    
    if not os.path.exists(full_log_path):
        print(f"Waiting for ZKTeco device to be connected and log file '{log_file_name}' to exist at '{mount_point}'...")
        return # No log file, so nothing to process yet

    print(f"\nFound log file: {full_log_path}")

    device_serial_from_logs = "UNKNOWN_USB_DEVICE" # Default, try to get from logs if possible

    try:
        # Read all logs from the file
        with open(full_log_path, 'r') as f:
            log_lines = f.readlines()

        if not log_lines:
            print("Log file is empty.")
            return

        # Prepare for processing
        new_logs_processed = 0
        latest_timestamp_in_batch = datetime.min
        
        # Get the last sync timestamp for this specific device (if known)
        # You might need to derive device_serial from the file contents or a user config
        # For this example, let's just use the first log's device_serial as primary key
        
        all_parsed_logs = []
        for line in log_lines:
            parsed_log = parse_zk_log_line(line)
            if parsed_log:
                all_parsed_logs.append(parsed_log)
                if device_serial_from_logs == "UNKNOWN_USB_DEVICE":
                    device_serial_from_logs = parsed_log['device_serial'] # Use first log's serial
        
        if not all_parsed_logs:
            print("No valid logs to process after parsing.")
            return

        # Sort logs by timestamp to ensure chronological processing
        all_parsed_logs.sort(key=lambda x: x['timestamp'])

        last_synced_dt = last_sync_timestamps.get(device_serial_from_logs, datetime.min)
        print(f"Last sync for {device_serial_from_logs}: {last_synced_dt}")

        for log_data in all_parsed_logs:
            if log_data['timestamp'] > last_synced_dt:
                push_to_zoho(log_data, device_serial_from_logs)
                new_logs_processed += 1
                if log_data['timestamp'] > latest_timestamp_in_batch:
                    latest_timestamp_in_batch = log_data['timestamp']
        
        if new_logs_processed > 0:
            last_sync_timestamps[device_serial_from_logs] = latest_timestamp_in_batch
            print(f"Processed {new_logs_processed} new logs. Updated last sync for {device_serial_from_logs} to {latest_timestamp_in_batch}")
            
            # --- CRITICAL: Move or Delete the processed log file ---
            # To prevent reprocessing the same logs.
            # Make sure the device allows writing/deleting.
            # Consider backing it up before deleting.
            
            # Option 1: Move to a 'processed_logs' folder on the USB drive
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
            
            # Rename with a timestamp to avoid overwriting if device has same filename
            new_file_name = f"{os.path.basename(full_log_path).replace('.dat', '')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.dat"
            shutil.move(full_log_path, os.path.join(processed_dir, new_file_name))
            print(f"Moved processed log file to: {os.path.join(processed_dir, new_file_name)}")
            
            # Option 2 (More risky): Delete the file
            # os.remove(full_log_path)
            # print(f"Deleted processed log file: {full_log_path}")

        else:
            print("No new logs to push from this file.")
            # If no new logs, you might still want to move the file to avoid re-reading it
            # Or you can assume the device clears it.
            # For robustness, moving it is safer.
            new_file_name = f"{os.path.basename(full_log_path).replace('.dat', '')}_{datetime.now().strftime('%Y%m%d%H%M%S')}_no_new.dat"
            shutil.move(full_log_path, os.path.join(processed_dir, new_file_name))
            print(f"Moved already-processed log file to: {os.path.join(processed_dir, new_file_name)}")


    except FileNotFoundError:
        print(f"Log file '{full_log_path}' not found. Is the device connected?")
    except PermissionError:
        print(f"Permission denied to access '{full_log_path}'. Unmount/remount, or run as admin.")
    except Exception as e:
        print(f"An error occurred during file processing: {e}")

# --- MAIN LOOP (Manual Triggering or Scheduled Execution) ---
if __name__ == "__main__":
    print("="*50)
    print(" ZKTECO USB LOG FILE PROCESSOR")
    print("="*50)
    print(f"Expected ZKTeco mount point: {ZK_USB_MOUNT_POINT}")
    print(f"Expected log file: {ZK_LOG_FILE_NAME}")
    print("Connect your ZKTeco device via USB and ensure the log file is present.")
    print("Press Ctrl+C to stop.\n")

    # Initialize last sync timestamp for a dummy USB device serial (replace with actual logic if multiple devices)
    last_sync_timestamps["YOUR_USB_DEVICE_SERIAL"] = datetime.now() - timedelta(days=7) # Start pulling logs from last week for testing

    while True:
        process_zkteco_usb_logs(ZK_USB_MOUNT_POINT, ZK_LOG_FILE_NAME)
        # This loop will run indefinitely, checking for files every 30 seconds
        # In a real deployment, this might be triggered manually after device connection,
        # or you'd need a more advanced way to detect USB insertion.
        time.sleep(30) # Check every 30 seconds