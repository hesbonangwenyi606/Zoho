import os
import requests
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
APP_OWNER = os.getenv("ZOHO_APP_OWNER")
APP_NAME = os.getenv("ZOHO_APP_NAME")
ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")

WORKERS_REPORT = os.getenv("WORKERS_REPORT", "All_Workers")
RAW_LOGS_REPORT = os.getenv("RAW_LOGS_REPORT", "Raw_Attendance_Logs_Form_Report")
DEVICES_REPORT = os.getenv("DEVICES_REPORT", "All_Devices")
DAILY_ATTENDANCE_REPORT = os.getenv("DAILY_ATTENDANCE_REPORT", "Daily_Attendance_Report")


def get_access_token():
    url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    try:
        response = requests.post(url, params=params, timeout=20)
        data = response.json()
        return data.get("access_token"), data, response.status_code
    except Exception as e:
        return None, {"error": str(e)}, None


def test_report(token, report_link):
    url = f"https://creator.{ZOHO_DOMAIN}/api/v2/{APP_OWNER}/{APP_NAME}/report/{report_link}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    params = {"from": 1, "limit": 1}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)


def main():
    token, data, status = get_access_token()
    if not token:
        print("Failed to generate access token.")
        print(f"Status: {status}")
        print(f"Response: {data}")
        return

    print("Testing report access (non-destructive)...")
    for name, report in [
        ("Workers", WORKERS_REPORT),
        ("Raw_Attendance_Logs_Form", RAW_LOGS_REPORT),
        ("Devices", DEVICES_REPORT),
        ("Daily_Attendance", DAILY_ATTENDANCE_REPORT),
    ]:
        status, resp = test_report(token, report)
        print(f"\n{name} report: {report}")
        print(f"Status Code: {status}")
        if status in (200, 201):
            print("OK")
        else:
            print(f"Error: {resp}")


if __name__ == "__main__":
    main()
