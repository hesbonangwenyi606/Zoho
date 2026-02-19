import requests
import json

# Your credentials from previous steps
CLIENT_ID = "1000.Q04IW1AMGYUVAPGQSJ68S6YPQLS0AW"
CLIENT_SECRET = "4ce9bcff0c9d5fdb90d9ff22f8d63fbd98aab484ea"
REFRESH_TOKEN = "1000.ca6b2d55dd76bb3b4afe4014726e1fb7.63ea74bc9c501844e975cd92874144b4"

def refresh_access_token():
    """Generates a new access token using the refresh token."""
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        new_token = response.json().get("access_token")
        print("✅ Access Token Refreshed!")
        return new_token
    else:
        print("❌ Failed to refresh token:", response.text)
        return None

def get_worker_info(worker_id, access_token):
    """Fetches data for a specific worker ID."""
    url = "https://creator.zoho.com/api/v2/wavemarkpropertieslimited/real-estate-wages-system/report/All_Workers"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    params = {
        "criteria": f"(Worker_ID=={worker_id})"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    # If token expired (401), refresh it and try again once
    if response.status_code == 401:
        print("🔄 Token expired, refreshing...")
        new_token = refresh_access_token()
        if new_token:
            headers["Authorization"] = f"Zoho-oauthtoken {new_token}"
            response = requests.get(url, headers=headers, params=params)
            
    return response.json()

# --- TEST THE CONNECTION ---
if __name__ == "__main__":
    # 1. Get a fresh token
    token = refresh_access_token()
    
    # 2. Try to fetch the user that was just matched (ID 17)
    if token:
        data = get_worker_info(17, token)
        print(json.dumps(data, indent=4))