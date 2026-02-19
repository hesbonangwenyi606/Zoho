import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

url = "https://accounts.zoho.com/oauth/v2/token"
params = {
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "refresh_token",
}

response = requests.post(url, params=params)
data = response.json()

if "access_token" in data:
    print("New access token:", data["access_token"])
    # Optionally, update your .env
    with open(".env", "r") as f:
        lines = f.readlines()
    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("ZOHO_ACCESS_TOKEN="):
                f.write(f"ZOHO_ACCESS_TOKEN={data['access_token']}\n")
            else:
                f.write(line)
else:
    print("Error refreshing token:", data)
