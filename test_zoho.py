import os
import requests
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")     # wavemarkpropertieslimited
FORM_LINK_NAME = "Raw_Attendance_Logs_Form" # Your form link name
ZOHO_DOMAIN = "zoho.com"

# Variations of App Link Name to try
app_name_variants = [
    "real-estate-wages-system",   # original
    "realestatewagessystem",      # remove hyphens
    "real_estate_wages_system"    # underscores
]

# --- Get OAuth token ---
def get_access_token():
    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    data = response.json()
    return data.get("access_token")

# --- Test URL ---
def test_url(token, app_name):
    url = f"https://creator.{ZOHO_DOMAIN}/api/v2/{APP_OWNER}/{app_name}/form/{FORM_LINK_NAME}/record/add"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "data": {
            "ZKTeco_User_ID": "TEST",
            "Worker_ID": "W001",
            "Timestamp": "2026-02-08T10:00:00",
            "Event_Type": "IN",
            "Device_ID": "ZKTeco_9500_10R",
            "Raw_JSON": "{\"test\":\"data\"}"
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

# --- Main ---
def main():
    token = get_access_token()
    if not token:
        print("❌ Failed to generate access token.")
        return

    print("🔍 Testing different App Link Name variants...")
    for app_name in app_name_variants:
        print(f"\nTesting App Name: {app_name}")
        status, resp = test_url(token, app_name)
        print(f"Status Code: {status}")
        print(f"Response: {resp}")
        if status in [200, 201]:
            print(f"✅ Success! Working API URL found with app name: {app_name}")
            break
    else:
        print("❌ None of the variants worked. Double-check owner/form names or contact Zoho Support.")

if __name__ == "__main__":
    main()
