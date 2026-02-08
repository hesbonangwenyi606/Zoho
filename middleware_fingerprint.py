import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from ctypes import *
import os
import sys

print("🟢 Script started...")  # Debug print

# ====================================
# LOAD ENVIRONMENT VARIABLES
# ====================================
load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")
APP_NAME = os.getenv("ZOHO_APP_NAME")

DEVICE_ID = "ZK9500_USB_FINGERPRINT"

# ====================================
# LOAD ZKTECO SDK DLL
# ====================================
SDK_FILENAME = "zkfp.dll"  # Make sure this DLL is in the same folder
SDK_PATH = os.path.join(os.getcwd(), SDK_FILENAME)

if not os.path.exists(SDK_PATH):
    print(f"❌ ERROR: {SDK_FILENAME} not found in {os.getcwd()}")
    sys.exit(1)

try:
    zkfp = WinDLL(SDK_PATH)
    print(f"🟢 Loaded {SDK_FILENAME} successfully")
except Exception as e:
    print(f"❌ Failed to load DLL: {e}")
    sys.exit(1)

# ====================================
# ZOHO AUTH
# ====================================
def get_access_token():
    try:
        url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token"
        }
        r = requests.post(url, params=params)
        r.raise_for_status()
        print("🟢 Zoho access token retrieved")
        return r.json()["access_token"]
    except Exception as e:
        print(f"❌ Zoho token error: {e}")
        return None

# ====================================
# PUSH TO ZOHO
# ====================================
def push_to_zoho(user_id, event="IN"):
    token = get_access_token()
    if not token:
        print("❌ Cannot push to Zoho, missing token")
        return

    url = f"https://creator.zoho.com/api/v2/{APP_OWNER}/{APP_NAME}/form/Raw_Attendance_Logs/record"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "ZKTeco_User_ID": str(user_id),
            "Timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "Event_Type": event,
            "Device_ID": DEVICE_ID
        }
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        print(f"✅ Attendance synced for User {user_id}")
    except Exception as e:
        print(f"❌ Zoho API error: {e}")

# ====================================
# FINGERPRINT DEVICE INIT
# ====================================
def init_device():
    print("🟢 Initializing fingerprint SDK...")
    if zkfp.ZKFPM_Init() != 0:
        print("❌ Failed to initialize SDK")
        sys.exit(1)

    count = zkfp.ZKFPM_GetDeviceCount()
    print(f"🟢 Devices detected: {count}")
    if count <= 0:
        print("❌ No fingerprint device found")
        sys.exit(1)

    handle = zkfp.ZKFPM_OpenDevice(0)
    if handle == 0:
        print("❌ Failed to open fingerprint device")
        sys.exit(1)

    print("🟢 Fingerprint device opened successfully")
    return handle

# ====================================
# CAPTURE FINGERPRINT
# ====================================
def capture_fingerprint(handle):
    template = create_string_buffer(2048)
    template_len = c_int(2048)

    ret = zkfp.ZKFPM_AcquireFingerprint(handle, None, template, byref(template_len))
    if ret == 0:
        print("🟢 Fingerprint captured")
        return template.raw[:template_len.value]
    else:
        print("⚠️ No fingerprint detected")
        return None

# ====================================
# MATCH FINGERPRINT (MOCK)
# ====================================
def match_fingerprint(template_bytes):
    """
    TODO: Replace this with real fingerprint-to-user matching logic.
    Currently returns a mock user ID.
    """
    return "1001"

# ====================================
# MAIN LOOP
# ====================================
if __name__ == "__main__":
    device_handle = init_device()
    print("🟢 Fingerprint reader ready. Place finger...")

    while True:
        template = capture_fingerprint(device_handle)
        if template:
            user_id = match_fingerprint(template)
            if user_id:
                push_to_zoho(user_id)
                time.sleep(2)  # Prevent double scan
        time.sleep(0.5)  # Short delay before next scan
