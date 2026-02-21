# import os
# import time
# import requests
# import argparse
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2

# # ==========================================================
# # 1. CONFIGURATION
# # ==========================================================
# load_dotenv()

# ZOHO_DOMAIN = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER = os.getenv("APP_OWNER")
# APP_NAME = os.getenv("APP_NAME")
# CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")

# WORKERS_REPORT = "All_Workers"
# ATTENDANCE_FORM = "Daily_Attendance"
# DEFAULT_PROJECT_ID = "4838902000000391493"

# TOKEN_CACHE = {"token": None, "expires_at": 0}
# API_DOMAIN = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"

# # ==========================================================
# # 2. AUTHENTICATION
# # ==========================================================
# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
#         return TOKEN_CACHE["token"]

#     url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {
#         "refresh_token": REFRESH_TOKEN,
#         "client_id": CLIENT_ID,
#         "client_secret": CLIENT_SECRET,
#         "grant_type": "refresh_token",
#     }

#     try:
#         response = requests.post(url, data=data, timeout=20)
#         result = response.json()
#         if "access_token" in result:
#             TOKEN_CACHE["token"] = result["access_token"]
#             TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#             return TOKEN_CACHE["token"]
#         else:
#             print("Authentication Error:", result)
#     except Exception as e:
#         print(f"Authentication Exception: {e}")
#     return None

# # ==========================================================
# # 3. FIND WORKER
# # ==========================================================
# def find_worker(user_id):
#     token = get_access_token()
#     if not token:
#         print("No access token available.")
#         return None

#     headers = {"Authorization": f"Zoho-oauthtoken {token}"}
#     report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f'(ZKTeco_User_ID2 == {int(user_id)})'

#     try:
#         response = requests.get(report_url, headers=headers, params={"criteria": criteria})
#         data = response.json().get("data", [])
#         if data:
#             return data[0]
#     except Exception as e:
#         print("Error while finding worker:", e)
#     return None

# # ==========================================================
# # 4. HELPER: FORMAT TOTAL TIME ("Xh Ym")
# # ==========================================================
# def format_total_time(total_seconds):
#     hours, remainder = divmod(total_seconds, 3600)
#     minutes = int(round(remainder / 60))  # round to nearest minute
#     return f"{int(hours)}h {minutes}m"

# # ==========================================================
# # 5. LOG ATTENDANCE (AUTO CHECK-IN / CHECK-OUT)
# # ==========================================================
# def log_attendance_auto(worker_record_id, project_id):
#     token = get_access_token()
#     if not token:
#         print("No access token available.")
#         return

#     headers = {"Authorization": f"Zoho-oauthtoken {token}"}
#     now = datetime.now()
#     today_str = now.strftime("%d-%b-%Y")

#     # Get worker details
#     worker_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#     r_worker = requests.get(worker_url, headers=headers)
#     worker_data = r_worker.json().get("data", {})

#     full_name = worker_data.get("Full_Name", "N/A")
#     role_name = worker_data.get("Roles", "N/A")
#     proj_lookup_id = project_id or DEFAULT_PROJECT_ID
#     attendance_form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"

#     # Check if attendance exists today
#     criteria_today = f'(Worker_ID_Lookup == "{worker_record_id}" && Date == "{today_str}")'
#     r_check = requests.get(
#         attendance_form_url.replace("/form/", "/report/"),
#         headers=headers,
#         params={"criteria": criteria_today}
#     )
#     data_today = r_check.json().get("data", [])

#     if data_today:
#         # CHECK-OUT
#         att = data_today[0]
#         attendance_id = att["ID"]
#         first_in_str = att.get("First_In")
#         last_out_str = att.get("Last_Out")

#         if last_out_str:
#             print(f"{full_name} has already checked out today at {last_out_str}.")
#         else:
#             try:
#                 first_in = datetime.strptime(first_in_str, "%d-%b-%Y %H:%M:%S")
#             except:
#                 first_in = now

#             total_seconds = (now - first_in).total_seconds()
#             total_hours = total_seconds / 3600
#             total_time_str = format_total_time(total_seconds)

#             payload = {
#                 "data": {
#                     "Last_Out": now.strftime("%d-%b-%Y %H:%M:%S"),
#                     "Total_Hours": total_hours,           # float for calculations
#                     "Total_Time_Str": total_time_str      # human-readable "Xh Ym"
#                 }
#             }

#             requests.put(
#                 f"{attendance_form_url}/{attendance_id}",
#                 headers=headers,
#                 json=payload
#             )

#             print(f"{full_name} checked OUT at {now.strftime('%H:%M')}")
#             print(f"Total Time Worked: {total_time_str}")

#     else:
#         # CHECK-IN
#         r_all = requests.get(
#             attendance_form_url.replace("/form/", "/report/"),
#             headers=headers,
#             params={"criteria": f'(Worker_ID_Lookup == "{worker_record_id}")'}
#         )
#         total_days = len(r_all.json().get("data", [])) + 1

#         payload = {
#             "data": {
#                 "Worker_ID_Lookup": worker_record_id,
#                 "Worker_Name": worker_record_id,
#                 "Projects": proj_lookup_id,
#                 "Projects_Assigned": proj_lookup_id,
#                 "Date": today_str,
#                 "First_In": now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Worker_Full_Name": full_name,
#                 "Roles": role_name,
#                 "Total_Days_Worked": total_days
#             }
#         }

#         requests.post(attendance_form_url, headers=headers, json=payload)
#         print(f"{full_name} checked IN at {now.strftime('%H:%M')}")

#     print_today_summary(worker_record_id)

# # ==========================================================
# # 6. PRINT TODAY SUMMARY
# # ==========================================================
# def print_today_summary(worker_record_id):
#     token = get_access_token()
#     if not token:
#         print("No access token available.")
#         return

#     headers = {"Authorization": f"Zoho-oauthtoken {token}"}
#     today_str = datetime.now().strftime("%d-%b-%Y")
#     attendance_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_FORM}"

#     attendance_data = []
#     for _ in range(5):
#         response = requests.get(
#             attendance_url,
#             headers=headers,
#             params={"criteria": f'(Worker_ID_Lookup == "{worker_record_id}" && Date == "{today_str}")'}
#         )
#         attendance_data = response.json().get("data", [])
#         if attendance_data:
#             break
#         time.sleep(1)

#     if attendance_data:
#         att = attendance_data[0]
#         first_in = att.get("First_In", "N/A")
#         last_out = att.get("Last_Out") or "Not checked out yet"
#         total_time_str = att.get("Total_Time_Str", "N/A")

#         print("\nToday's Attendance Summary:")
#         print(f"First In  : {first_in}")
#         print(f"Last Out  : {last_out}")
#         print(f"Total Time: {total_time_str}")  # <-- always "Xh Ym"
#     else:
#         print("\nRemember to CheckOut at the evening for your Dairy-Pay to be updated")

# # ==========================================================
# # 7. ENROLL FINGERPRINT + ATTENDANCE
# # ==========================================================
# def enroll_fingerprint_auto(user_id):
#     zkfp2 = ZKFP2()
#     zkfp2.Init()

#     if zkfp2.GetDeviceCount() == 0:
#         print("No fingerprint device found.")
#         return

#     zkfp2.OpenDevice(0)

#     try:
#         worker = find_worker(user_id)
#         if not worker:
#             print("Sorry, you are no longer a participant here.")
#             print("Please contact the Admin")
#             return

#         worker_record_id = worker["ID"]
#         full_name = worker.get("Full_Name", "N/A")
#         proj_id = worker.get("Projects_Assigned", {}).get("ID") or DEFAULT_PROJECT_ID
#         existing_template = worker.get("Fingerprint_Template")

#         if not existing_template or existing_template.strip() == "":
#             print("Place your finger on the scanner to enroll fingerprint.")

#             capture = None
#             while not capture:
#                 capture = zkfp2.AcquireFingerprint()
#                 time.sleep(0.1)

#             template_hex = bytes(list(capture[0])).hex()
#             token = get_access_token()
#             headers = {"Authorization": f"Zoho-oauthtoken {token}"}
#             update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"

#             response = requests.put(
#                 update_url,
#                 headers=headers,
#                 json={"data": {"Fingerprint_Template": template_hex}}
#             )

#             print(f"Fingerprint saved for {full_name}. Response: {response.status_code}")

#         log_attendance_auto(worker_record_id, proj_id)

#     finally:
#         zkfp2.CloseDevice()
#         zkfp2.Terminate()

# # ==========================================================
# # 8. MAIN ENTRY POINT
# # ==========================================================
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--user-id", type=str, required=True)
#     args = parser.parse_args()
#     enroll_fingerprint_auto(args.user_id)



# import os, ast, time, json, requests, argparse, base64
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2

# # ==========================================================
# # 1. CONFIGURATION
# # ==========================================================
# load_dotenv()

# ZOHO_DOMAIN    = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER      = "wavemarkpropertieslimited"
# APP_NAME       = "real-estate-wages-system"
# CLIENT_ID      = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET  = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN  = os.getenv("ZOHO_REFRESH_TOKEN")

# WORKERS_REPORT    = "All_Workers"
# ATTENDANCE_FORM   = "Daily_Attendance"
# ATTENDANCE_REPORT = "Daily_Attendance_Report"

# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE = {"token": None, "expires_at": 0}
# API_DOMAIN  = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE = "checkin_today.json"

# # ==========================================================
# # 2. NETWORK RETRY WRAPPER
# # ==========================================================
# MAX_RETRIES   = 4
# RETRY_DELAY   = 3
# TIMEOUT       = 20
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# def zoho_request(method, url, *, retries=MAX_RETRIES, expected_statuses=(200,201), **kwargs):
#     kwargs.setdefault("timeout", TIMEOUT)
#     for attempt in range(1, retries + 1):
#         try:
#             response = requests.request(method, url, **kwargs)
#             if response.status_code in expected_statuses:
#                 return response
#             if response.status_code in RETRYABLE_STATUSES:
#                 wait = RETRY_DELAY * attempt
#                 print(f"[RETRY] HTTP {response.status_code} on {method} {url}, retrying in {wait}s")
#                 time.sleep(wait)
#                 continue
#             return response
#         except (requests.exceptions.ConnectionError,
#                 requests.exceptions.Timeout,
#                 OSError) as e:
#             wait = RETRY_DELAY * attempt
#             print(f"[RETRY] Network error: {e}, retrying in {wait}s")
#             time.sleep(wait)
#         except requests.exceptions.RequestException as e:
#             print(f"[ERROR] Unrecoverable request error: {e}")
#             return None
#     print(f"[ERROR] All {retries} attempts failed for {method} {url}")
#     return None

# # ==========================================================
# # 3. LOCAL CHECK-IN LOCK
# # ==========================================================
# def load_checkin_lock():
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#             if data.get("date") == today_str:
#                 return data
#         except Exception:
#             pass
#     return {"date": today_str, "checked_in": {}, "checked_out": {}}

# def is_checked_in_today(worker_record_id):
#     return load_checkin_lock()["checked_in"].get(worker_record_id)

# def is_checked_out_today(worker_record_id):
#     return worker_record_id in load_checkin_lock().get("checked_out", {})

# def mark_checked_in(worker_record_id, checkin_time_str):
#     lock = load_checkin_lock()
#     lock["checked_in"][worker_record_id] = checkin_time_str
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def mark_checked_out(worker_record_id):
#     lock = load_checkin_lock()
#     lock["checked_in"].pop(worker_record_id, None)
#     lock.setdefault("checked_out", {})[worker_record_id] = datetime.now().strftime("%H:%M:%S")
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# # ==========================================================
# # 4. AUTHENTICATION
# # ==========================================================
# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
#         return TOKEN_CACHE["token"]
#     url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {
#         "refresh_token": REFRESH_TOKEN,
#         "client_id":     CLIENT_ID,
#         "client_secret": CLIENT_SECRET,
#         "grant_type":    "refresh_token",
#     }
#     r = zoho_request("POST", url, data=data)
#     if r is None:
#         print("[ERROR] Token request failed")
#         return None
#     result = r.json()
#     if "access_token" in result:
#         TOKEN_CACHE["token"] = result["access_token"]
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     print("Authentication Error:", result)
#     return None

# def auth_headers():
#     token = get_access_token()
#     if not token:
#         raise RuntimeError("Could not obtain access token.")
#     return {"Authorization": f"Zoho-oauthtoken {token}"}

# # ==========================================================
# # 5. WORKER HELPERS
# # ==========================================================
# def find_worker(user_id):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r:
#         data = r.json().get("data", [])
#         if data:
#             return data[0]
#     return None

# def get_worker_record(worker_record_id):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#     r = zoho_request("GET", url, headers=auth_headers())
#     return r.json().get("data", {}) if r else {}

# def is_fingerprint_enrolled(full_record):
#     raw = full_record.get("Fingerprint_Enrolled", [])
#     if isinstance(raw, str):
#         try: raw = ast.literal_eval(raw)
#         except Exception: raw = []
#     return isinstance(raw, list) and "YES" in raw

# def mark_fingerprint_enrolled(worker_record_id):
#     update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#     for payload_value in (["YES"], "YES"):
#         r = zoho_request("PUT", update_url, headers=auth_headers(),
#                          json={"data": {"Fingerprint_Enrolled": payload_value}})
#         if r and r.status_code in (200, 201):
#             time.sleep(2)
#             refreshed = get_worker_record(worker_record_id)
#             if is_fingerprint_enrolled(refreshed):
#                 return True
#     print("[ERROR] Could not update Fingerprint_Enrolled to YES.")
#     return False

# # ==========================================================
# # 6. FORMAT TOTAL TIME
# # ==========================================================
# def format_total_time(total_seconds):
#     hours, remainder = divmod(int(total_seconds), 3600)
#     minutes = round(remainder / 60)
#     return f"{hours}h {minutes}m"

# # ==========================================================
# # 7. ATTENDANCE HELPERS
# # ==========================================================
# def get_today_attendance(worker_record_id):
#     today_str = datetime.now().strftime("%d-%b-%Y")
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     criteria = f'(Worker_ID_Lookup == "{worker_record_id}" && Date == "{today_str}")'
#     for _ in range(8):
#         r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#         if r is None:
#             return None
#         if r.status_code == 404:
#             print(f"[ERROR] 404 on report '{ATTENDANCE_REPORT}'")
#             return None
#         data = r.json().get("data", [])
#         if data: return data[0]
#         time.sleep(2)
#     return {}

# # ==========================================================
# # 8. LOG ATTENDANCE WITH SINGLE DAILY CHECK-IN
# # ==========================================================
# def log_attendance_auto(worker_record_id, project_id, full_name, role_name):
#     now = datetime.now()
#     today_str = now.strftime("%d-%b-%Y")
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     proj_lookup = project_id or DEFAULT_PROJECT_ID

#     if is_checked_out_today(worker_record_id):
#         print(f"⛔ {full_name} has already checked IN and OUT today. See you tomorrow!")
#         return

#     checkin_time = is_checked_in_today(worker_record_id)
#     if checkin_time:
#         # CHECK-OUT
#         try: first_in_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
#         except Exception: first_in_dt = now
#         total_secs = (now - first_in_dt).total_seconds()
#         total_time_str = format_total_time(total_secs)

#         existing = get_today_attendance(worker_record_id)
#         if existing and existing.get("ID"):
#             att_id = existing["ID"]
#             r = zoho_request("PUT", f"{form_url}/{att_id}", headers=auth_headers(),
#                              json={"data": {
#                                  "Last_Out": now.strftime("%d-%b-%Y %H:%M:%S"),
#                                  "Total_Hours": total_secs / 3600,
#                                  "Total_Time_Str": total_time_str
#                              }})
#             if r and r.status_code in (200,201):
#                 mark_checked_out(worker_record_id)
#                 print(f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}")
#                 print(f"   Total Time Worked: {total_time_str}")
#             else:
#                 status = r.status_code if r else "No response"
#                 body   = r.text[:300] if r else ""
#                 print(f"[ERROR] Check-out failed ({status}): {body}")
#         else:
#             print("⚠ Attendance record already exists for today. Contact Admin.")
#         return

#     # CHECK-IN
#     checkin_str = now.strftime("%d-%b-%Y %H:%M:%S")
#     r = zoho_request("POST", form_url, headers=auth_headers(),
#                      json={"data": {
#                          "Worker_ID_Lookup": worker_record_id,
#                          "Worker_Name": worker_record_id,
#                          "Projects": proj_lookup,
#                          "Projects_Assigned": proj_lookup,
#                          "Date": today_str,
#                          "First_In": checkin_str,
#                          "Worker_Full_Name": full_name,
#                          "Roles": role_name
#                      }})
#     if r and r.status_code in (200,201):
#         mark_checked_in(worker_record_id, checkin_str)
#         print(f"✅ {full_name} checked IN at {now.strftime('%H:%M')}")
#         print("   Remember to check OUT in the evening for your Daily-Pay to be updated.")
#     else:
#         status = r.status_code if r else "No response"
#         body   = r.text[:300] if r else ""
#         print(f"[ERROR] Check-in failed ({status}): {body}")

# # ==========================================================
# # 9. ENROLL & VERIFY FINGERPRINT
# # ==========================================================
# def enroll_fingerprint_auto(user_id):
#     zkfp2 = ZKFP2()
#     zkfp2.Init()

#     if zkfp2.GetDeviceCount() == 0:
#         print("No fingerprint device found.")
#         return

#     zkfp2.OpenDevice(0)

#     try:
#         worker = find_worker(user_id)
#         if not worker:
#             print("You are not registered in the system. Contact Admin.")
#             return

#         worker_record_id = worker["ID"]
#         full_name = worker.get("Full_Name", "N/A")
#         role_name = worker.get("Roles", "N/A")

#         proj_raw = worker.get("Projects_Assigned", {})
#         if isinstance(proj_raw, str):
#             try: proj_raw = ast.literal_eval(proj_raw)
#             except Exception: proj_raw = {}
#         proj_id = proj_raw.get("ID") or DEFAULT_PROJECT_ID

#         full_record = get_worker_record(worker_record_id)
#         enrolled_templates = full_record.get("Fingerprint_Templates", [])
#         if isinstance(enrolled_templates, str):
#             try: enrolled_templates = ast.literal_eval(enrolled_templates)
#             except Exception: enrolled_templates = []

#         # Already enrolled? → verify
#         if enrolled_templates:
#             print(f"Welcome back, {full_name}! Place your finger to verify.")
#             capture = None
#             while not capture:
#                 capture = zkfp2.AcquireFingerprint()
#                 time.sleep(0.1)

#             template_bytes = bytes(list(capture[0]))
#             match_found = False
#             for t_b64 in enrolled_templates:
#                 t_bytes = base64.b64decode(t_b64)
#                 if zkfp2.MatchFingerprint(template_bytes, t_bytes):
#                     match_found = True
#                     break

#             if match_found:
#                 print("✅ Fingerprint verified!")
#                 log_attendance_auto(worker_record_id, proj_id, full_name, role_name)
#                 return
#             else:
#                 print("Fingerprint did not match any stored template. Contact Admin.")
#                 return

#         # Not enrolled → enroll
#         print(f"Welcome {full_name}! Place your finger on the scanner to enroll.")
#         capture = None
#         while not capture:
#             capture = zkfp2.AcquireFingerprint()
#             time.sleep(0.1)

#         template_bytes = bytes(list(capture[0]))
#         template_b64 = base64.b64encode(template_bytes).decode()
#         enrolled_templates.append(template_b64)

#         update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#         zoho_request("PUT", update_url, headers=auth_headers(),
#                      json={"data": {"Fingerprint_Templates": enrolled_templates}})

#         mark_fingerprint_enrolled(worker_record_id)
#         print(f"✅ Fingerprint enrolled for {full_name}.")

#         log_attendance_auto(worker_record_id, proj_id, full_name, role_name)

#     finally:
#         zkfp2.CloseDevice()
#         zkfp2.Terminate()

# # ==========================================================
# # 10. MAIN
# # ==========================================================
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--user-id", type=str, required=True)
#     args = parser.parse_args()
#     enroll_fingerprint_auto(args.user_id)




import os, ast, time, json, requests, argparse, base64
from datetime import datetime
from dotenv import load_dotenv
from pyzkfp import ZKFP2

# ==========================================================
# 1. CONFIGURATION
# ==========================================================
load_dotenv()

ZOHO_DOMAIN    = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER      = "wavemarkpropertieslimited"
APP_NAME       = "real-estate-wages-system"
CLIENT_ID      = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET  = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN  = os.getenv("ZOHO_REFRESH_TOKEN")

WORKERS_REPORT    = "All_Workers"
ATTENDANCE_FORM   = "Daily_Attendance"
ATTENDANCE_REPORT = "Daily_Attendance_Report"

DEFAULT_PROJECT_ID = "4838902000000391493"
TOKEN_CACHE = {"token": None, "expires_at": 0}
API_DOMAIN  = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
CHECKIN_LOCK_FILE = "checkin_today.json"

MAX_RETRIES   = 4
RETRY_DELAY   = 3
TIMEOUT       = 20
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# ==========================================================
# 2. NETWORK RETRY WRAPPER
# ==========================================================
def zoho_request(method, url, *, retries=MAX_RETRIES, expected_statuses=(200,201), **kwargs):
    kwargs.setdefault("timeout", TIMEOUT)
    for attempt in range(1, retries + 1):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code in expected_statuses:
                return response
            if response.status_code in RETRYABLE_STATUSES:
                wait = RETRY_DELAY * attempt
                print(f"[RETRY] HTTP {response.status_code} on {method} {url}, retrying in {wait}s")
                time.sleep(wait)
                continue
            return response
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                OSError) as e:
            wait = RETRY_DELAY * attempt
            print(f"[RETRY] Network error: {e}, retrying in {wait}s")
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Unrecoverable request error: {e}")
            return None
    print(f"[ERROR] All {retries} attempts failed for {method} {url}")
    return None

# ==========================================================
# 3. LOCAL CHECK-IN LOCK
# ==========================================================
def load_checkin_lock():
    today_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(CHECKIN_LOCK_FILE):
        try:
            with open(CHECKIN_LOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") == today_str:
                return data
        except Exception:
            pass
    return {"date": today_str, "checked_in": {}, "checked_out": {}}

def is_checked_in_today(worker_record_id):
    return load_checkin_lock()["checked_in"].get(worker_record_id)

def is_checked_out_today(worker_record_id):
    return worker_record_id in load_checkin_lock().get("checked_out", {})

def mark_checked_in(worker_record_id, checkin_time_str):
    lock = load_checkin_lock()
    lock["checked_in"][worker_record_id] = checkin_time_str
    with open(CHECKIN_LOCK_FILE, "w") as f:
        json.dump(lock, f)

def mark_checked_out(worker_record_id):
    lock = load_checkin_lock()
    lock["checked_in"].pop(worker_record_id, None)
    lock.setdefault("checked_out", {})[worker_record_id] = datetime.now().strftime("%H:%M:%S")
    with open(CHECKIN_LOCK_FILE, "w") as f:
        json.dump(lock, f)

# ==========================================================
# 4. AUTHENTICATION
# ==========================================================
def get_access_token():
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return TOKEN_CACHE["token"]
    url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
    }
    r = zoho_request("POST", url, data=data)
    if r is None:
        print("[ERROR] Token request failed")
        return None
    result = r.json()
    if "access_token" in result:
        TOKEN_CACHE["token"] = result["access_token"]
        TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
        return TOKEN_CACHE["token"]
    print("Authentication Error:", result)
    return None

def auth_headers():
    token = get_access_token()
    if not token:
        raise RuntimeError("Could not obtain access token.")
    return {"Authorization": f"Zoho-oauthtoken {token}"}

# ==========================================================
# 5. WORKER HELPERS
# ==========================================================
def find_worker(user_id):
    url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    criteria = f"(ZKTeco_User_ID2 == {int(user_id)})"
    r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
    if r:
        data = r.json().get("data", [])
        if data:
            return data[0]
    return None

def get_worker_record(worker_record_id):
    url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
    r = zoho_request("GET", url, headers=auth_headers())
    return r.json().get("data", {}) if r else {}

def is_fingerprint_enrolled(full_record):
    raw = full_record.get("Fingerprint_Enrolled", [])
    if isinstance(raw, str):
        try: raw = ast.literal_eval(raw)
        except Exception: raw = []
    return isinstance(raw, list) and "YES" in raw

def mark_fingerprint_enrolled(worker_record_id):
    update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
    for payload_value in (["YES"], "YES"):
        r = zoho_request("PUT", update_url, headers=auth_headers(),
                         json={"data": {"Fingerprint_Enrolled": payload_value}})
        if r and r.status_code in (200, 201):
            time.sleep(2)
            refreshed = get_worker_record(worker_record_id)
            if is_fingerprint_enrolled(refreshed):
                return True
    print("[ERROR] Could not update Fingerprint_Enrolled to YES.")
    return False

# ==========================================================
# 6. FORMAT TOTAL TIME
# ==========================================================
def format_total_time(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes = round(remainder / 60)
    return f"{hours}h {minutes}m"

# ==========================================================
# 7. ATTENDANCE HELPERS
# ==========================================================
def get_today_attendance(worker_record_id):
    today_str = datetime.now().strftime("%d-%b-%Y")
    url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
    criteria = f'(Worker_ID_Lookup == "{worker_record_id}" && Date == "{today_str}")'
    for _ in range(8):
        r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
        if r is None:
            return None
        if r.status_code == 404:
            print(f"[ERROR] 404 on report '{ATTENDANCE_REPORT}'")
            return None
        data = r.json().get("data", [])
        if data: return data[0]
        time.sleep(2)
    return {}

# ==========================================================
# 8. LOG ATTENDANCE WITH SINGLE DAILY CHECK-IN
# ==========================================================
def log_attendance_auto(worker_record_id, project_id, full_name, role_name):
    now = datetime.now()
    today_str = now.strftime("%d-%b-%Y")
    form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
    proj_lookup = project_id or DEFAULT_PROJECT_ID

    if is_checked_out_today(worker_record_id):
        print(f"⛔ {full_name} has already checked IN and OUT today. See you tomorrow!")
        return

    checkin_time = is_checked_in_today(worker_record_id)
    if checkin_time:
        # CHECK-OUT
        try: first_in_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
        except Exception: first_in_dt = now
        total_secs = (now - first_in_dt).total_seconds()
        total_time_str = format_total_time(total_secs)

        existing = get_today_attendance(worker_record_id)
        if existing and existing.get("ID"):
            att_id = existing["ID"]
            r = zoho_request("PUT", f"{form_url}/{att_id}", headers=auth_headers(),
                             json={"data": {
                                 "Last_Out": now.strftime("%d-%b-%Y %H:%M:%S"),
                                 "Total_Hours": total_secs / 3600,
                                 "Total_Time_Str": total_time_str
                             }})
            if r and r.status_code in (200,201):
                mark_checked_out(worker_record_id)
                print(f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}")
                print(f"   Total Time Worked: {total_time_str}")
            else:
                status = r.status_code if r else "No response"
                body   = r.text[:300] if r else ""
                print(f"[ERROR] Check-out failed ({status}): {body}")
        else:
            print("Sorry enrollement available only once per day.")
            print("Please Contact Admin.")
        return

    # CHECK-IN
    checkin_str = now.strftime("%d-%b-%Y %H:%M:%S")
    r = zoho_request("POST", form_url, headers=auth_headers(),
                     json={"data": {
                         "Worker_ID_Lookup": worker_record_id,
                         "Worker_Name": worker_record_id,
                         "Projects": proj_lookup,
                         "Projects_Assigned": proj_lookup,
                         "Date": today_str,
                         "First_In": checkin_str,
                         "Worker_Full_Name": full_name,
                         "Roles": role_name
                     }})
    if r and r.status_code in (200,201):
        mark_checked_in(worker_record_id, checkin_str)
        print(f"✅ {full_name} checked IN at {now.strftime('%H:%M')}")
        print("   Remember to check OUT in the evening for your Daily-Pay to be updated.")
    else:
        status = r.status_code if r else "No response"
        body   = r.text[:300] if r else ""
        print(f"[ERROR] Check-in failed ({status}): {body}")

# ==========================================================
# 9. DUPLICATE FINGERPRINT DETECTION
# ==========================================================
def is_duplicate_fingerprint(new_template_bytes):
    url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    r = zoho_request("GET", url, headers=auth_headers())
    if not r or r.status_code != 200:
        print("[ERROR] Cannot fetch workers to check duplicates.")
        return False
    workers = r.json().get("data", [])
    zkfp2 = ZKFP2()
    zkfp2.Init()
    for worker in workers:
        templates = worker.get("Fingerprint_Templates", [])
        if isinstance(templates, str):
            try: templates = ast.literal_eval(templates)
            except Exception: templates = []
        for t_b64 in templates:
            t_bytes = base64.b64decode(t_b64)
            if zkfp2.MatchFingerprint(new_template_bytes, t_bytes):
                print(f"[DUPLICATE] Fingerprint matches worker: {worker.get('Full_Name','Unknown')}")
                zkfp2.Terminate()
                return True
    zkfp2.Terminate()
    return False

# ==========================================================
# 10. ENROLL & VERIFY FINGERPRINT
# ==========================================================
def enroll_fingerprint_auto(user_id):
    zkfp2 = ZKFP2()
    zkfp2.Init()
    if zkfp2.GetDeviceCount() == 0:
        print("No fingerprint device found.")
        return
    zkfp2.OpenDevice(0)

    try:
        worker = find_worker(user_id)
        if not worker:
            print("You are not registered in the system.")
            print("Please Contact Admin.")
            return

        worker_record_id = worker["ID"]
        full_name = worker.get("Full_Name","N/A")
        role_name = worker.get("Roles","N/A")

        proj_raw = worker.get("Projects_Assigned", {})
        if isinstance(proj_raw, str):
            try: proj_raw = ast.literal_eval(proj_raw)
            except Exception: proj_raw = {}
        proj_id = proj_raw.get("ID") or DEFAULT_PROJECT_ID

        full_record = get_worker_record(worker_record_id)
        enrolled_templates = full_record.get("Fingerprint_Templates", [])
        if isinstance(enrolled_templates, str):
            try: enrolled_templates = ast.literal_eval(enrolled_templates)
            except Exception: enrolled_templates = []

        # Already enrolled? Verify
        if enrolled_templates:
            print(f"Welcome back, {full_name}! Place your finger to verify.")
            capture = None
            while not capture:
                capture = zkfp2.AcquireFingerprint()
                time.sleep(0.1)
            template_bytes = bytes(list(capture[0]))
            match_found = False
            for t_b64 in enrolled_templates:
                t_bytes = base64.b64decode(t_b64)
                if zkfp2.MatchFingerprint(template_bytes, t_bytes):
                    match_found = True
                    break
            if match_found:
                print("✅ Fingerprint verified!")
                log_attendance_auto(worker_record_id, proj_id, full_name, role_name)
                return
            else:
                print("Fingerprint did not match any stored template.")
                print("Please Contact Admin")
                return

        # Not enrolled → enroll
        print(f"Welcome {full_name}! Place your finger on the scanner to enroll.")
        capture = None
        while not capture:
            capture = zkfp2.AcquireFingerprint()
            time.sleep(0.1)

        template_bytes = bytes(list(capture[0]))

        # Duplicate check
        if is_duplicate_fingerprint(template_bytes):
            print(" Sorry this fingerprint is already registered.")
            print("Please Contact Admin")
            return

        template_b64 = base64.b64encode(template_bytes).decode()
        enrolled_templates.append(template_b64)

        update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
        zoho_request("PUT", update_url, headers=auth_headers(),
                     json={"data": {"Fingerprint_Templates": enrolled_templates}})

        mark_fingerprint_enrolled(worker_record_id)
        print(f"✅ Fingerprint enrolled for {full_name}.")
        log_attendance_auto(worker_record_id, proj_id, full_name, role_name)

    finally:
        zkfp2.CloseDevice()
        zkfp2.Terminate()

# ==========================================================
# 11. MAIN
# ==========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=str, required=True)
    args = parser.parse_args()
    enroll_fingerprint_auto(args.user_id)
    # enroll_fingerprint_auto(args.Worker_ID_Lookup)
