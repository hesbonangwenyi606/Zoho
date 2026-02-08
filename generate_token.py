import requests
import os
from dotenv import load_dotenv

# Load Client ID and Secret from .env file
load_dotenv()
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")

def get_refresh_token():
    # --- I pasted your code here ---
    code = "1000.535e23eec745602a3e360fd226fd0dd4.f3ab1615c222b3f8a03fc64760b40519"
    
    print(f"🔄 Exchanging code: {code[:15]}...")

    url = "https://accounts.zoho.com/oauth/v2/token"
    
    # Prepare the request
    params = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code"
    }

    try:
        response = requests.post(url, data=params)
        data = response.json()

        # Check for success
        if "refresh_token" in data:
            print("\n✅ SUCCESS! Here is your Permanent Refresh Token:")
            print("==================================================")
            print(data["refresh_token"])
            print("==================================================")
            print("1. COPY the token above.")
            print("2. OPEN your .env file.")
            print("3. REPLACE 'ZOHO_REFRESH_TOKEN' with this new value.")
            print("4. SAVE the .env file.")
        else:
            print("\n❌ ERROR:")
            print(f"Server said: {data.get('error')}")
            print("Reason: The code might have expired or Client ID/Secret in .env is wrong.")

    except Exception as e:
        print(f"❌ Network Error: {e}")

if __name__ == "__main__":
    get_refresh_token()