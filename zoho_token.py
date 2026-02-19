# zoho_token.py
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_API_BASE = os.getenv("ZOHO_API_BASE", "https://www.zohoapis.com")

# Internal cache
_access_token = None
_last_refresh = 0

def get_access_token(force_refresh=False):
    """
    Returns a valid Zoho access token. Auto-refreshes if expired.
    """
    global _access_token, _last_refresh

    # Refresh if forced or expired (~58 min)
    if force_refresh or not _access_token or (time.time() - _last_refresh > 3500):
        token_url = f"{ZOHO_API_BASE}/oauth/v2/token"
        data = {
            "refresh_token": ZOHO_REFRESH_TOKEN,
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token"
        }
        resp = requests.post(token_url, data=data)
        token_data = resp.json()

        if "access_token" not in token_data:
            raise Exception(f"Failed to get Zoho access token: {token_data}")

        _access_token = token_data["access_token"]
        _last_refresh = time.time()
        print("Obtained new Zoho access token ✅")

    return _access_token
