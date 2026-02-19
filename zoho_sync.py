import requests
import json

# CREDENTIALS (From your Postman screenshots)
CLIENT_ID = "1000.Q04IW1AMGYUVAPGQSJ68S6YPQLS0AW"
CLIENT_SECRET = "4ce9bcff0c9d5fdb90d9ff22f8d63fbd98aab484ea"
REFRESH_TOKEN = "1000.9bedc8e4adfa3ae64554a4a2031f744e.28051fa5e42fa605aa7fb8979e048ad6"

def get_access_token():
    """Automates login: Uses the refresh token to get a working access token."""
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"❌ Token Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def fetch_worker_by_id(worker_id):
    """Fetches the specific worker details from Zoho Creator."""
    access_token = get_access_token()
    if not access_token:
        return None

    # This is the exact URL and criteria we used in Postman
    url = "https://creator.zoho.com/api/v2/wavemarkpropertieslimited/real-estate-wages-system/report/All_Workers"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    params = {"criteria": f"(Worker_ID=={worker_id})"}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                return data[0] # Return the first worker found
        return None
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return None