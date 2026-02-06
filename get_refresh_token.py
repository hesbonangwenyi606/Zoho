import requests

# Your details from your notepad
client_id = "1000.X8OHDXTUMT7K4UM7MTERMP1SWNQCPW"
client_secret = "4660b7bca3696132842ac1b2dffd8b7cbf9d3356d0"
# PASTE the NEW code from the blue box in Zoho API Console below
auth_code = "1000.81c1e72fd68b809d91d463c6ab0a89b2.49e9c3348cc31d70e12747042499890c"

url = "https://accounts.zoho.com/oauth/v2/token"

data = {
    "code": auth_code,
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "authorization_code"
}

response = requests.post(url, data=data)

print("--- RESPONSE FROM ZOHO ---")
print(response.text)