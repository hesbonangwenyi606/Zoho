import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_token():
    url = f"https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN"),
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "grant_type": "refresh_token"
    }
    return requests.post(url, data=data).json().get("access_token")

def verify_id_23():
    token = get_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    
    # URL to fetch user 23
    url = f"https://www.zohoapis.com/creator/v2/{os.getenv('APP_OWNER')}/{os.getenv('APP_NAME')}/report/All_Workers"
    params = {"criteria": '(ZKTeco_User_ID == "23")'}
    
    response = requests.get(url, headers=headers, params=params).json()
    
    if "data" in response and len(response["data"]) > 0:
        user = response["data"][0]
        template = user.get("Fingerprint_Template")
        
        print("\n--- DATABASE CHECK ---")
        print(f"Name: {user.get('Full_Name')}")
        print(f"ID:   {user.get('ZKTeco_User_ID')}")
        
        if template:
            print(f"✅ FINGERPRINT FOUND! (Length: {len(template)} characters)")
            print(f"Template starts with: {template[:30]}...")
        else:
            print("FINGERPRINT COLUMN IS EMPTY.")
    else:
        print("User 23 not found in database.")

verify_id_23()