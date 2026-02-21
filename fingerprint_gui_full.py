# import os, ast, time, json, requests, argparse, base64, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import ttk, messagebox
# import subprocess

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

# MAX_RETRIES   = 4
# RETRY_DELAY   = 3
# TIMEOUT       = 20
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# # ==========================================================
# # 2. NETWORK WRAPPER
# # ==========================================================
# def zoho_request(method, url, *, retries=MAX_RETRIES, expected_statuses=(200,201), **kwargs):
#     kwargs.setdefault("timeout", TIMEOUT)
#     for attempt in range(1, retries + 1):
#         try:
#             response = requests.request(method, url, **kwargs)
#             if response.status_code in expected_statuses:
#                 return response
#             if response.status_code in RETRYABLE_STATUSES:
#                 wait = RETRY_DELAY * attempt
#                 continue
#             return response
#         except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, OSError) as e:
#             wait = RETRY_DELAY * attempt
#             time.sleep(wait)
#         except requests.exceptions.RequestException:
#             return None
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
#         return None
#     result = r.json()
#     if "access_token" in result:
#         TOKEN_CACHE["token"] = result["access_token"]
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
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
#         data = r.json().get("data", [])
#         if data: return data[0]
#         time.sleep(2)
#     return {}

# # ==========================================================
# # 8. LOG ATTENDANCE
# # ==========================================================
# def log_attendance_auto(worker_record_id, project_id, full_name, role_name, log_func):
#     now = datetime.now()
#     today_str = now.strftime("%d-%b-%Y")
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     proj_lookup = project_id or DEFAULT_PROJECT_ID

#     if is_checked_out_today(worker_record_id):
#         log_func(f"⛔ {full_name} has already checked IN and OUT today")
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
#                 log_func(f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}")
#                 log_func(f"   Total Time Worked: {total_time_str}")
#             else:
#                 log_func("[ERROR] Check-out failed")
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
#         log_func(f"✅ {full_name} checked IN at {now.strftime('%H:%M')}")
#     else:
#         log_func("[ERROR] Check-in failed")

# # ==========================================================
# # 9. DUPLICATE FINGERPRINT CHECK
# # ==========================================================
# def is_duplicate_fingerprint(new_template_bytes):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     r = zoho_request("GET", url, headers=auth_headers())
#     if not r or r.status_code != 200: return False
#     workers = r.json().get("data", [])
#     zkfp2 = ZKFP2()
#     zkfp2.Init()
#     for worker in workers:
#         templates = worker.get("Fingerprint_Templates", [])
#         if isinstance(templates, str):
#             try: templates = ast.literal_eval(templates)
#             except Exception: templates = []
#         for t_b64 in templates:
#             t_bytes = base64.b64decode(t_b64)
#             if zkfp2.MatchFingerprint(new_template_bytes, t_bytes):
#                 zkfp2.Terminate()
#                 return True
#     zkfp2.Terminate()
#     return False

# # ==========================================================
# # 10. GUI APP
# # ==========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Zoho Fingerprint Middleware")
#         self.root.geometry("600x500")
#         self.root.resizable(False, False)
#         self.create_widgets()

#     def create_widgets(self):
#         tk.Label(self.root, text="Zoho Attendance Fingerprint System", font=("Arial", 16, "bold")).pack(pady=10)

#         # Status
#         status_frame = tk.Frame(self.root)
#         status_frame.pack(pady=10)
#         tk.Label(status_frame, text="Device Status:", font=("Arial", 12)).pack(side=tk.LEFT)
#         self.canvas = tk.Canvas(status_frame, width=30, height=30, highlightthickness=0)
#         self.canvas.pack(side=tk.LEFT, padx=10)
#         self.led = self.canvas.create_oval(5,5,25,25,fill="red")
#         self.status_label = tk.Label(status_frame, text="Disconnected", font=("Arial", 12))
#         self.status_label.pack(side=tk.LEFT)

#         # User ID input
#         input_frame = tk.Frame(self.root)
#         input_frame.pack(pady=15)
#         tk.Label(input_frame, text="User ID:", font=("Arial",12)).pack(side=tk.LEFT)
#         self.user_id_entry = tk.Entry(input_frame, width=20,font=("Arial",12))
#         self.user_id_entry.pack(side=tk.LEFT,padx=10)

#         # Buttons
#         button_frame = tk.Frame(self.root)
#         button_frame.pack(pady=10)
#         ttk.Button(button_frame,text="Check Device",command=self.check_device).grid(row=0,column=0,padx=5)
#         ttk.Button(button_frame,text="Enroll Fingerprint",command=self.enroll_fingerprint).grid(row=0,column=1,padx=5)
#         ttk.Button(button_frame,text="Send To Zoho",command=self.send_to_zoho).grid(row=0,column=2,padx=5)

#         # Log panel
#         tk.Label(self.root, text="System Logs:", font=("Arial", 12)).pack(pady=5)
#         self.log_text = tk.Text(self.root, height=15, width=70)
#         self.log_text.pack(pady=5)

#     # Logging
#     def log(self, msg):
#         self.log_text.insert(tk.END, msg+"\n")
#         self.log_text.see(tk.END)

#     def set_green(self,text="Connected"):
#         self.canvas.itemconfig(self.led, fill="#28a745")
#         self.status_label.config(text=text)

#     def set_red(self,text="Disconnected"):
#         self.canvas.itemconfig(self.led, fill="#dc3545")
#         self.status_label.config(text=text)

#     # Buttons functionality
#     def check_device(self):
#         try:
#             zk = ZKFP2()
#             zk.Init()
#             if zk.GetDeviceCount()>0:
#                 self.set_green("Device Connected")
#                 self.log("✔ Device found and ready")
#             else:
#                 self.set_red("No Device")
#                 self.log(" No fingerprint device found")
#             zk.Terminate()
#         except Exception as e:
#             self.set_red("Error")
#             self.log(f"Device check error: {str(e)}")

#     def enroll_fingerprint(self):
#         user_id = self.user_id_entry.get()
#         if not user_id:
#             messagebox.showerror("Error","Please enter User ID")
#             return
#         threading.Thread(target=self.run_enrollment, args=(user_id,),daemon=True).start()

#     def run_enrollment(self,user_id):
#         try:
#             zk = ZKFP2()
#             zk.Init()
#             if zk.GetDeviceCount()==0:
#                 self.set_red("No Device")
#                 self.log("No fingerprint device found")
#                 zk.Terminate()
#                 return
#             zk.OpenDevice(0)
#             self.set_green("Device Ready")

#             # Lookup worker
#             worker = find_worker(user_id)
#             if not worker:
#                 self.set_red("User Not Found")
#                 self.log("Worker not found in Zoho")
#                 zk.CloseDevice()
#                 zk.Terminate()
#                 return

#             worker_record_id = worker["ID"]
#             full_name = worker.get("Full_Name","N/A")
#             role_name = worker.get("Roles","N/A")
#             proj_id = worker.get("Projects_Assigned", {}).get("ID", DEFAULT_PROJECT_ID)

#             full_record = get_worker_record(worker_record_id)
#             enrolled_templates = full_record.get("Fingerprint_Templates",[])
#             if isinstance(enrolled_templates,str):
#                 try: enrolled_templates=ast.literal_eval(enrolled_templates)
#                 except: enrolled_templates=[]

#             # Already enrolled
#             if enrolled_templates:
#                 self.log(f"Welcome back {full_name}, place finger to verify")
#                 capture=None
#                 while not capture:
#                     capture = zk.AcquireFingerprint()
#                     time.sleep(0.1)
#                 template_bytes = bytes(list(capture[0]))
#                 match=False
#                 for t_b64 in enrolled_templates:
#                     if zk.MatchFingerprint(template_bytes, base64.b64decode(t_b64)):
#                         match=True
#                         break
#                 if match:
#                     self.log("✅ Fingerprint verified")
#                     log_attendance_auto(worker_record_id, proj_id, full_name, role_name,self.log)
#                     zk.CloseDevice()
#                     zk.Terminate()
#                     return
#                 else:
#                     self.log(" Fingerprint did not match")
#                     zk.CloseDevice()
#                     zk.Terminate()
#                     return

#             # New enrollment
#             self.log(f"Welcome {full_name}, place finger to enroll")
#             capture=None
#             while not capture:
#                 capture = zk.AcquireFingerprint()
#                 time.sleep(0.1)
#             template_bytes = bytes(list(capture[0]))

#             # Duplicate check
#             if is_duplicate_fingerprint(template_bytes):
#                 self.log("Fingerprint already registered")
#                 zk.CloseDevice()
#                 zk.Terminate()
#                 return

#             # Save
#             enrolled_templates.append(base64.b64encode(template_bytes).decode())
#             update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#             zoho_request("PUT", update_url, headers=auth_headers(),
#                          json={"data":{"Fingerprint_Templates":enrolled_templates}})
#             mark_fingerprint_enrolled(worker_record_id)
#             self.log(f"✅ Fingerprint enrolled for {full_name}")
#             log_attendance_auto(worker_record_id, proj_id, full_name, role_name,self.log)

#             zk.CloseDevice()
#             zk.Terminate()

#         except Exception as e:
#             self.set_red("Error")
#             self.log(f"Enrollment error: {str(e)}")

#     def send_to_zoho(self):
#         self.log("Sending data to Zoho... (already integrated in enrollment)")
#         self.log("✔ Done")

# # ==========================================================
# # 11. MAIN
# # ==========================================================
# if __name__=="__main__":
#     root=tk.Tk()
#     app=FingerprintGUI(root)
#     root.mainloop()


# import os, ast, time, json, requests, base64, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import messagebox

# # ================= CONFIG =================
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

# MAX_RETRIES   = 4
# RETRY_DELAY   = 3
# TIMEOUT       = 20
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# # ================= NETWORK =================
# def zoho_request(method, url, *, retries=MAX_RETRIES, expected_statuses=(200,201), **kwargs):
#     kwargs.setdefault("timeout", TIMEOUT)
#     for attempt in range(1, retries+1):
#         try:
#             response = requests.request(method, url, **kwargs)
#             if response.status_code in expected_statuses: return response
#             if response.status_code in RETRYABLE_STATUSES: time.sleep(RETRY_DELAY*attempt); continue
#             return response
#         except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, OSError):
#             time.sleep(RETRY_DELAY*attempt)
#         except requests.exceptions.RequestException:
#             return None
#     return None

# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"]-60:
#         return TOKEN_CACHE["token"]
#     url = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
#     r = zoho_request("POST", url, data=data)
#     if r and "access_token" in r.json():
#         TOKEN_CACHE["token"] = r.json()["access_token"]
#         TOKEN_CACHE["expires_at"] = now + int(r.json().get("expires_in",3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     if not token: raise RuntimeError("Could not obtain Zoho access token.")
#     return {"Authorization": f"Zoho-oauthtoken {token}"}

# # ================= WORKER HELPERS =================
# def find_worker(user_id):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r: data = r.json().get("data", [])
#     else: data = []
#     return data[0] if data else None

# def get_worker_record(worker_record_id):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#     r = zoho_request("GET", url, headers=auth_headers())
#     return r.json().get("data", {}) if r else {}

# def is_fingerprint_enrolled(full_record):
#     raw = full_record.get("Fingerprint_Enrolled", [])
#     if isinstance(raw, str):
#         try: raw = ast.literal_eval(raw)
#         except: raw=[]
#     return isinstance(raw,list) and "YES" in raw

# def mark_fingerprint_enrolled(worker_record_id):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#     for val in (["YES"], "YES"):
#         r = zoho_request("PUT", url, headers=auth_headers(), json={"data":{"Fingerprint_Enrolled":val}})
#         if r and r.status_code in (200,201):
#             refreshed = get_worker_record(worker_record_id)
#             if is_fingerprint_enrolled(refreshed): return True
#     return False

# # ================= ATTENDANCE =================
# def load_checkin_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE,"r") as f: data = json.load(f)
#             if data.get("date")==today: return data
#         except: pass
#     return {"date":today,"checked_in":{},"checked_out":{}}

# def is_checked_in_today(worker_record_id):
#     return load_checkin_lock()["checked_in"].get(worker_record_id)

# def is_checked_out_today(worker_record_id):
#     return worker_record_id in load_checkin_lock().get("checked_out",{})

# def mark_checked_in(worker_record_id, checkin_time_str):
#     lock = load_checkin_lock()
#     lock["checked_in"][worker_record_id] = checkin_time_str
#     with open(CHECKIN_LOCK_FILE,"w") as f: json.dump(lock,f)

# def mark_checked_out(worker_record_id):
#     lock = load_checkin_lock()
#     lock["checked_in"].pop(worker_record_id,None)
#     lock.setdefault("checked_out",{})[worker_record_id] = datetime.now().strftime("%H:%M:%S")
#     with open(CHECKIN_LOCK_FILE,"w") as f: json.dump(lock,f)

# def get_today_attendance(worker_record_id):
#     today_str = datetime.now().strftime("%d-%b-%Y")
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     criteria = f'(Worker_ID_Lookup == "{worker_record_id}" && Date == "{today_str}")'
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria":criteria})
#     if r and r.status_code==200:
#         data = r.json().get("data",[])
#         return data[0] if data else {}
#     return {}

# def log_attendance_auto(worker_record_id, project_id, full_name, role_name, is_checkout=False):
#     now = datetime.now()
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     proj_lookup = project_id or DEFAULT_PROJECT_ID

#     if is_checkout:
#         checkin_time = is_checked_in_today(worker_record_id)
#         if not checkin_time:
#             return False,"Cannot check-out without check-in"
#         first_in_dt = datetime.strptime(checkin_time,"%d-%b-%Y %H:%M:%S")
#         total_secs = (now - first_in_dt).total_seconds()
#         total_time_str = f"{int(total_secs//3600)}h {int((total_secs%3600)/60)}m"

#         existing = get_today_attendance(worker_record_id)
#         if existing and existing.get("ID"):
#             att_id = existing["ID"]
#             r = zoho_request("PUT", f"{form_url}/{att_id}", headers=auth_headers(),
#                              json={"data":{"Last_Out":now.strftime("%d-%b-%Y %H:%M:%S"),
#                                             "Total_Hours":total_secs/3600,
#                                             "Total_Time_Str":total_time_str}})
#             if r and r.status_code in (200,201):
#                 mark_checked_out(worker_record_id)
#                 return True,f"Checked OUT at {now.strftime('%H:%M')}. Total: {total_time_str}"
#         return False,"Check-out failed"
#     else:
#         checkin_str = now.strftime("%d-%b-%Y %H:%M:%S")
#         r = zoho_request("POST", form_url, headers=auth_headers(),
#                          json={"data":{"Worker_ID_Lookup":worker_record_id,
#                                        "Worker_Name":worker_record_id,
#                                        "Projects":proj_lookup,
#                                        "Projects_Assigned":proj_lookup,
#                                        "Date":now.strftime("%d-%b-%Y"),
#                                        "First_In":checkin_str,
#                                        "Worker_Full_Name":full_name,
#                                        "Roles":role_name}})
#         if r and r.status_code in (200,201):
#             mark_checked_in(worker_record_id,checkin_str)
#             return True,f"Checked IN at {now.strftime('%H:%M')}"
#         return False,"Check-in failed"

# # ================= DUPLICATE =================
# def is_duplicate_fingerprint(new_template_bytes):
#     url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     r = zoho_request("GET", url, headers=auth_headers())
#     if not r or r.status_code != 200: return False
#     workers = r.json().get("data",[])
#     zkfp2 = ZKFP2(); zkfp2.Init()
#     for worker in workers:
#         templates = worker.get("Fingerprint_Templates",[])
#         if isinstance(templates,str):
#             try: templates = ast.literal_eval(templates)
#             except: templates=[]
#         for t_b64 in templates:
#             t_bytes = base64.b64decode(t_b64)
#             if zkfp2.MatchFingerprint(new_template_bytes,t_bytes):
#                 zkfp2.Terminate()
#                 return True
#     zkfp2.Terminate()
#     return False

# # ================= GUI =================
# class FingerprintApp:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Zoho Fingerprint Dashboard")
#         self.root.geometry("800x500")
#         self.root.configure(bg="black")

#         # --- User ID input
#         self.label = tk.Label(root, text="Enter User ID:", font=("Arial",24), fg="white", bg="black")
#         self.label.pack(pady=20)

#         self.entry = tk.Entry(root,font=("Arial",24))
#         self.entry.pack(pady=10)
#         self.entry.focus()
#         self.entry.bind("<Return>", lambda e:self.start_process_thread())

#         # --- Status
#         self.status_label = tk.Label(root,text="", font=("Arial",20), fg="white", bg="black")
#         self.status_label.pack(pady=20)

#         # --- Fingerprint device
#         self.zkfp2 = ZKFP2(); self.zkfp2.Init()
#         if self.zkfp2.GetDeviceCount()==0:
#             messagebox.showerror("Error","No fingerprint device found."); root.destroy(); return
#         self.zkfp2.OpenDevice(0)
#         self.current_worker = None

#         self.check_next_user()

#     def start_process_thread(self):
#         threading.Thread(target=self.process_user,daemon=True).start()

#     def process_user(self):
#         user_id = self.entry.get().strip()
#         if not user_id: return

#         self.status_label.config(text="Checking user...", fg="yellow")
#         worker = find_worker(user_id)
#         if not worker:
#             self.status_label.config(text="User not found", fg="red")
#             self.reset_for_next_user()
#             return

#         self.current_worker = worker
#         worker_record_id = worker["ID"]
#         full_record = get_worker_record(worker_record_id)
#         checked_in = is_checked_in_today(worker_record_id)
#         checked_out = is_checked_out_today(worker_record_id)

#         if checked_in and not checked_out:
#             # CHECK-OUT
#             success,msg = log_attendance_auto(worker_record_id, DEFAULT_PROJECT_ID,
#                                              worker.get("Full_Name","N/A"), worker.get("Roles","N/A"),
#                                              is_checkout=True)
#             self.status_label.config(text=msg, fg="green" if success else "red")
#         elif not checked_in:
#             # CHECK-IN + Enrollment
#             if not is_fingerprint_enrolled(full_record):
#                 self.status_label.config(text="Place finger on scanner for ENROLLMENT...", fg="yellow"); self.root.update()
#                 capture=None
#                 while not capture: capture=self.zkfp2.AcquireFingerprint(); time.sleep(0.05)
#                 template_bytes = bytes(list(capture[0]))
#                 if is_duplicate_fingerprint(template_bytes):
#                     self.status_label.config(text="Duplicate fingerprint!", fg="red")
#                     self.reset_for_next_user(); return
#                 template_b64 = base64.b64encode(template_bytes).decode()
#                 templates = full_record.get("Fingerprint_Templates",[])
#                 if isinstance(templates,str):
#                     try: templates=ast.literal_eval(templates)
#                     except: templates=[]
#                 templates.append(template_b64)
#                 update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}/{worker_record_id}"
#                 zoho_request("PUT", update_url, headers=auth_headers(), json={"data":{"Fingerprint_Templates":templates}})
#                 mark_fingerprint_enrolled(worker_record_id)

#             success,msg = log_attendance_auto(worker_record_id, DEFAULT_PROJECT_ID,
#                                              worker.get("Full_Name","N/A"), worker.get("Roles","N/A"))
#             self.status_label.config(text=msg, fg="green" if success else "red")
#         else:
#             self.status_label.config(text="Already Checked IN & OUT today", fg="red")

#         self.reset_for_next_user()

#     def reset_for_next_user(self):
#         self.entry.delete(0, tk.END)
#         self.entry.focus()
#         self.current_worker=None

#     def check_next_user(self):
#         self.entry.focus()
#         self.root.after(500, self.check_next_user)

#     def on_close(self):
#         self.zkfp2.CloseDevice()
#         self.zkfp2.Terminate()
#         self.root.destroy()

# if __name__=="__main__":
#     root=tk.Tk()
#     app = FingerprintApp(root)
#     root.protocol("WM_DELETE_WINDOW", app.on_close)
#     root.mainloop()



# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"
# MAX_RETRIES        = 4
# RETRY_DELAY        = 3
# TIMEOUT            = 20
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# # ===========================================================
# # NETWORK HELPER
# # ===========================================================
# def zoho_request(method, url, *, retries=MAX_RETRIES,
#                  expected_statuses=(200, 201), **kwargs):
#     kwargs.setdefault("timeout", TIMEOUT)
#     for attempt in range(1, retries + 1):
#         try:
#             resp = requests.request(method, url, **kwargs)
#             if resp.status_code in expected_statuses:
#                 return resp
#             if resp.status_code in RETRYABLE_STATUSES:
#                 time.sleep(RETRY_DELAY * attempt)
#                 continue
#             return resp
#         except (requests.exceptions.ConnectionError,
#                 requests.exceptions.Timeout, OSError):
#             time.sleep(RETRY_DELAY * attempt)
#     return None

# # ===========================================================
# # CHECKIN LOCK
# #
# # All lock functions key on the ZKTeco user_id (the short
# # number the operator types in). The Zoho internal worker ID
# # is NEVER stored here. This keeps on_id_change instant and
# # the key consistent throughout the whole flow.
# # ===========================================================
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

# def is_checked_in_today(zk_user_id):
#     return load_checkin_lock()["checked_in"].get(str(zk_user_id))

# def is_checked_out_today(zk_user_id):
#     return str(zk_user_id) in load_checkin_lock().get("checked_out", {})

# def mark_checked_in(zk_user_id, time_str):
#     lock = load_checkin_lock()
#     lock["checked_in"][str(zk_user_id)] = time_str
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def mark_checked_out(zk_user_id):
#     lock = load_checkin_lock()
#     lock["checked_in"].pop(str(zk_user_id), None)
#     lock.setdefault("checked_out", {})[str(zk_user_id)] = \
#         datetime.now().strftime("%H:%M:%S")
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def get_worker_status(zk_user_id):
#     key = str(zk_user_id)
#     if is_checked_out_today(key):
#         return "done"
#     if is_checked_in_today(key):
#         return "checked_in"
#     return "none"

# # ===========================================================
# # AUTHENTICATION
# # ===========================================================
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
#     if r:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     if not token:
#         raise RuntimeError("Could not obtain Zoho access token.")
#     return {"Authorization": f"Zoho-oauthtoken {token}"}

# # ===========================================================
# # WORKER LOOKUP
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(),
#                      params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         if data:
#             return data[0]
#     return None

# # ===========================================================
# # ATTENDANCE
# #   worker_id   = Zoho internal record ID  (API calls only)
# #   zk_user_id  = ZKTeco short numeric ID  (lock file key)
# # ===========================================================
# def log_attendance(worker_id, zk_user_id, project_id, full_name, action):
#     now    = datetime.now()
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     zk_key   = str(zk_user_id)

#     # Three date representations used in different contexts:
#     #   today_display -> value written into the Date field on POST (dd-MMM-yyyy)
#     #   today_iso     -> used in GET criteria filter              (yyyy-MM-dd)
#     #   today_mmdd    -> fallback Zoho stored format              (MM/dd/yyyy)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")
#     today_mmdd    = now.strftime("%m/%d/%Y")

#     # ----------------------------------------------------------
#     # CHECK-IN
#     # ----------------------------------------------------------
#     if action == "checkin":
#         if is_checked_out_today(zk_key):
#             return False, (
#                 f"{full_name} has already completed attendance for today. "
#                 "Only one check-in/out cycle is allowed per day."
#             )
#         if is_checked_in_today(zk_key):
#             t = is_checked_in_today(zk_key)
#             return False, (
#                 f"{full_name} already checked IN today at "
#                 f"{t.split(' ')[-1] if t else 'N/A'}. "
#                 "Please use Check-Out instead."
#             )

#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         r = zoho_request(
#             "POST", form_url,
#             headers=auth_headers(),
#             json={"data": {
#                 "Worker_ID_Lookup":  worker_id,
#                 "Worker_Name":       worker_id,
#                 "Projects":          project_id,
#                 "Projects_Assigned": project_id,
#                 "Date":              today_display,
#                 "First_In":          checkin_time,
#                 "Worker_Full_Name":  full_name,
#             }}
#         )
#         if r and r.status_code in (200, 201):
#             mark_checked_in(zk_key, checkin_time)
#             return True, f"[OK] {full_name} checked IN at {now.strftime('%H:%M')}"
#         err = r.text if r else "No response"
#         return False, (
#             f"[ERROR] Check-in failed "
#             f"(HTTP {r.status_code if r else '???'}): {err}"
#         )

#     # ----------------------------------------------------------
#     # CHECK-OUT
#     # ----------------------------------------------------------
#     elif action == "checkout":
#         if is_checked_out_today(zk_key):
#             t = load_checkin_lock().get("checked_out", {}).get(zk_key, "N/A")
#             return False, (
#                 f"{full_name} already checked OUT today at {t}. "
#                 "Only one check-in/out cycle is allowed per day."
#             )

#         checkin_time = is_checked_in_today(zk_key)
#         if not checkin_time:
#             return False, (
#                 f"{full_name} has not checked IN yet today. "
#                 "Please check IN first."
#             )

#         # Calculate hours worked
#         try:
#             first_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             first_dt = now
#         total_secs     = (now - first_dt).total_seconds()
#         total_hours    = total_secs / 3600
#         total_time_str = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

#         # Step 1: find the attendance record created at check-in.
#         #
#         # KEY FIX: Zoho Creator criteria on a Date field requires
#         # ISO format yyyy-MM-dd, NOT dd-MMM-yyyy (which is the write
#         # format). Using dd-MMM-yyyy in the criteria returns 0 results
#         # even though the record exists, causing checkout to fail.
#         #
#         # We try three strategies so the code survives any Zoho
#         # tenant date storage quirk:
#         report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#         records = []

#         # The report uses "Date_field" (not "Date") and the worker lookup
#         # column is "Worker_Name" (not "Worker_ID_Lookup") whose value is
#         # a dict: {"display_value": "...", "ID": "<zoho_worker_id>"}.
#         # In Zoho Creator criteria, lookup fields are matched by their ID
#         # using dot notation: Worker_Name.ID == "..."

#         # Strategy A: lookup ID + ISO date
#         crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_iso}")'
#         r = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#         if r and r.status_code == 200:
#             records = r.json().get("data", [])

#         # Strategy B: lookup ID + display date
#         if not records:
#             crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_display}")'
#             r = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#             if r and r.status_code == 200:
#                 records = r.json().get("data", [])

#         # Strategy C: worker only, match date in Python using the real field name
#         if not records:
#             crit = f'(Worker_Name.ID == "{worker_id}")'
#             r = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if str(rec.get("Date_field", "")).strip() in possible
#                 ]

#         # Strategy D: no filter, match worker ID + date in Python
#         if not records:
#             r = zoho_request("GET", report_url, headers=auth_headers())
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if rec.get("Worker_Name", {}).get("ID") == worker_id
#                     and str(rec.get("Date_field", "")).strip() in possible
#                 ]

#         if not records:
#             return False, (
#                 f"[ERROR] Check-out failed: attendance record not found.\n"
#                 f"   Worker Zoho ID : {worker_id}\n"
#                 f"   Dates tried    : {today_display} / {today_iso} / {today_mmdd}"
#             )

#         att_id  = records[0]["ID"]
#         # Zoho Creator v2: updates must use the REPORT endpoint, not form endpoint.
#         put_url = f"{report_url}/{att_id}"

#         # Step 2: update the record with Last_Out and totals
#         r2 = zoho_request(
#             "PUT", put_url,
#             headers=auth_headers(),
#             json={"data": {
#                 "Last_Out":       now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Total_Hours":    round(total_hours, 4),
#                 "Total_Time_Str": total_time_str,
#             }}
#         )
#         if r2 and r2.status_code in (200, 201):
#             mark_checked_out(zk_key)
#             return True, (
#                 f"[OK] {full_name} checked OUT at {now.strftime('%H:%M')} "
#                 f"| Total: {total_time_str}"
#             )
#         err = r2.text[:400] if r2 else "No response (timeout / connection error)"
#         return False, (
#             f"[ERROR] Check-out PUT failed\n"
#             f"   URL    : {put_url}\n"
#             f"   Status : {r2.status_code if r2 else 'timeout'}\n"
#             f"   Detail : {err}"
#         )

#     return False, "[ERROR] Unknown action"

# # ===========================================================
# # GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root  = root
#         self.root.title("Zoho Attendance Fingerprint System")
#         self.root.geometry("640x560")
#         self._busy = False
#         self._build_ui()

#     def _build_ui(self):
#         # Header bar
#         hdr = tk.Frame(self.root, bg="#2c3e50", pady=12)
#         hdr.pack(fill=tk.X)
#         tk.Label(hdr, text="Zoho Attendance System",
#                  font=("Arial", 15, "bold"),
#                  bg="#2c3e50", fg="white").pack()

#         # User ID input
#         inp = tk.Frame(self.root, pady=12)
#         inp.pack()
#         tk.Label(inp, text="User ID:", font=("Arial", 12)).pack(
#             side=tk.LEFT, padx=6)
#         self.user_entry = tk.Entry(inp, font=("Arial", 13), width=18)
#         self.user_entry.pack(side=tk.LEFT, padx=6)
#         self.user_entry.bind("<KeyRelease>", self._on_id_change)
#         self.user_entry.focus_set()

#         # Status label
#         self.status_lbl = tk.Label(
#             self.root, text="Enter a User ID to begin.",
#             font=("Arial", 10, "italic"), fg="gray")
#         self.status_lbl.pack(pady=4)

#         # Action buttons
#         btn_frame = tk.Frame(self.root, pady=6)
#         btn_frame.pack()

#         self.btn_in = tk.Button(
#             btn_frame, text="Check-In", width=16,
#             font=("Arial", 11, "bold"),
#             bg="#28a745", fg="white",
#             activebackground="#1e7e34",
#             disabledforeground="#999999",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkin")
#         )
#         self.btn_in.pack(side=tk.LEFT, padx=14, ipady=6)

#         self.btn_out = tk.Button(
#             btn_frame, text="Check-Out", width=16,
#             font=("Arial", 11, "bold"),
#             bg="#dc3545", fg="white",
#             activebackground="#bd2130",
#             disabledforeground="#999999",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkout")
#         )
#         self.btn_out.pack(side=tk.LEFT, padx=14, ipady=6)

#         # Divider
#         tk.Frame(self.root, height=1, bg="#cccccc").pack(
#             fill=tk.X, pady=6, padx=10)

#         # Activity log (read-only)
#         tk.Label(self.root, text="Activity Log:",
#                  font=("Arial", 11, "bold")).pack(anchor="w", padx=14)
#         log_frame = tk.Frame(self.root)
#         log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
#         sb = tk.Scrollbar(log_frame)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(
#             log_frame, height=14, width=74,
#             font=("Courier", 10),
#             yscrollcommand=sb.set,
#             state=tk.DISABLED
#         )
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#     # -------------------------------------------------------
#     # Thread-safe UI helpers
#     # -------------------------------------------------------
#     def log(self, msg):
#         def _do():
#             ts = datetime.now().strftime("%H:%M:%S")
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{ts}]  {msg}\n")
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _set_status(self, text, color="gray"):
#         self.root.after(
#             0, lambda: self.status_lbl.config(text=text, fg=color))

#     def _set_buttons(self, in_state, out_state):
#         def _do():
#             self.btn_in.config(state=in_state)
#             self.btn_out.config(state=out_state)
#         self.root.after(0, _do)

#     def _apply_status_ui(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "Attendance complete for today - no further action allowed.",
#                 "red")
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status(
#                 "Already checked IN today - Check-Out is now available.",
#                 "darkorange")
#         else:
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status(
#                 "Not yet checked in today - Check-In is available.",
#                 "darkgreen")

#     # -------------------------------------------------------
#     # ID field keystroke handler
#     # -------------------------------------------------------
#     def _on_id_change(self, _event=None):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Enter a User ID to begin.", "gray")
#             return
#         self._apply_status_ui(get_worker_status(uid))

#     # -------------------------------------------------------
#     # Button click
#     # -------------------------------------------------------
#     def _trigger(self, action):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         threading.Thread(
#             target=self._process, args=(uid, action), daemon=True
#         ).start()

#     # -------------------------------------------------------
#     # Background worker thread
#     # -------------------------------------------------------
#     def _process(self, zk_user_id, action):
#         zk          = None
#         device_open = False
#         try:
#             zk = ZKFP2()
#             zk.Init()
#             if zk.GetDeviceCount() == 0:
#                 self.log("No fingerprint device found.")
#                 return
#             zk.OpenDevice(0)
#             device_open = True
#             self.log("Place your finger on the scanner...")

#             worker = find_worker(zk_user_id)
#             if not worker:
#                 self.log("Worker not found in Zoho.")
#                 return

#             full_name      = worker.get("Full_Name", "N/A")
#             zoho_worker_id = worker["ID"]   # Zoho internal ID - API use only

#             # Guard: re-check with authoritative lock state
#             status = get_worker_status(zk_user_id)
#             if status == "done":
#                 self.log(
#                     f"{full_name} has already completed attendance today. "
#                     "No further action until tomorrow.")
#                 self._apply_status_ui(status)
#                 return
#             if status == "checked_in" and action == "checkin":
#                 t = is_checked_in_today(zk_user_id)
#                 self.log(
#                     f"{full_name} already checked IN at "
#                     f"{t.split(' ')[-1] if t else 'N/A'} today. "
#                     "Use Check-Out instead.")
#                 self._apply_status_ui(status)
#                 return
#             if status == "none" and action == "checkout":
#                 self.log(
#                     f"{full_name} has not checked IN yet today. "
#                     "Please check IN first.")
#                 self._apply_status_ui(status)
#                 return

#             # Fingerprint scan
#             capture = None
#             while not capture:
#                 capture = zk.AcquireFingerprint()
#                 time.sleep(0.1)
#             self.log("Fingerprint verified.")

#             # Post to Zoho
#             project_id = (
#                 worker.get("Projects_Assigned", {}).get("ID")
#                 or DEFAULT_PROJECT_ID
#             )
#             success, message = log_attendance(
#                 zoho_worker_id, zk_user_id, project_id, full_name, action
#             )
#             self.log(message)

#             if success:
#                 self._apply_status_ui(get_worker_status(zk_user_id))

#         except Exception as exc:
#             self.log(f"ERROR: {exc}")

#         finally:
#             if zk and device_open:
#                 try:
#                     zk.CloseDevice()
#                     zk.Terminate()
#                 except Exception:
#                     pass
#             self._busy = False

#             def _reset():
#                 self.user_entry.delete(0, tk.END)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status("Enter a User ID to begin.", "gray")
#                 self.log("-" * 50 + "\nReady for next user.")
#             self.root.after(0, _reset)

# # ===========================================================
# # MAIN
# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop()


# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"
# MAX_RETRIES        = 3          # reduced: PATCH is not safely idempotent
# RETRY_DELAY        = 2
# TIMEOUT            = 45         # increased from 20 → 45 seconds
# PATCH_TIMEOUT      = 60         # extra-long timeout specifically for PATCH
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# # ===========================================================
# # NETWORK HELPER
# # ===========================================================
# def zoho_request(method, url, *, retries=MAX_RETRIES,
#                  expected_statuses=(200, 201), timeout=None, **kwargs):
#     kwargs.setdefault("timeout", timeout or TIMEOUT)
#     for attempt in range(1, retries + 1):
#         try:
#             resp = requests.request(method, url, **kwargs)
#             if resp.status_code in expected_statuses:
#                 return resp
#             if resp.status_code in RETRYABLE_STATUSES:
#                 time.sleep(RETRY_DELAY * attempt)
#                 continue
#             return resp
#         except (requests.exceptions.ConnectionError,
#                 requests.exceptions.Timeout, OSError) as e:
#             if attempt == retries:
#                 return None
#             time.sleep(RETRY_DELAY * attempt)
#     return None

# # ===========================================================
# # CHECKIN LOCK
# # ===========================================================
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

# def is_checked_in_today(zk_user_id):
#     return load_checkin_lock()["checked_in"].get(str(zk_user_id))

# def is_checked_out_today(zk_user_id):
#     return str(zk_user_id) in load_checkin_lock().get("checked_out", {})

# def mark_checked_in(zk_user_id, time_str):
#     lock = load_checkin_lock()
#     lock["checked_in"][str(zk_user_id)] = time_str
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def mark_checked_out(zk_user_id):
#     lock = load_checkin_lock()
#     lock["checked_in"].pop(str(zk_user_id), None)
#     lock.setdefault("checked_out", {})[str(zk_user_id)] = \
#         datetime.now().strftime("%H:%M:%S")
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def get_worker_status(zk_user_id):
#     key = str(zk_user_id)
#     if is_checked_out_today(key):
#         return "done"
#     if is_checked_in_today(key):
#         return "checked_in"
#     return "none"

# # ===========================================================
# # AUTHENTICATION
# # ===========================================================
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
#     r = zoho_request("POST", url, data=data, timeout=30)
#     if r:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     if not token:
#         raise RuntimeError("Could not obtain Zoho access token.")
#     return {"Authorization": f"Zoho-oauthtoken {token}"}

# # ===========================================================
# # WORKER LOOKUP
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(),
#                      params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         if data:
#             return data[0]
#     return None

# # ===========================================================
# # ATTENDANCE
# # ===========================================================
# def log_attendance(worker_id, zk_user_id, project_id, full_name, action):
#     now      = datetime.now()
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     zk_key   = str(zk_user_id)

#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")
#     today_mmdd    = now.strftime("%m/%d/%Y")

#     # ----------------------------------------------------------
#     # CHECK-IN
#     # ----------------------------------------------------------
#     if action == "checkin":
#         if is_checked_out_today(zk_key):
#             return False, (
#                 f"{full_name} has already completed attendance for today. "
#                 "Only one check-in/out cycle is allowed per day."
#             )
#         if is_checked_in_today(zk_key):
#             t = is_checked_in_today(zk_key)
#             return False, (
#                 f"{full_name} already checked IN today at "
#                 f"{t.split(' ')[-1] if t else 'N/A'}. "
#                 "Please use Check-Out instead."
#             )

#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         # Resolve token ONCE before the POST
#         hdrs = auth_headers()
#         r = zoho_request(
#             "POST", form_url,
#             headers=hdrs,
#             json={"data": {
#                 "Worker_ID_Lookup":  worker_id,
#                 "Worker_Name":       worker_id,
#                 "Projects":          project_id,
#                 "Projects_Assigned": project_id,
#                 "Date":              today_display,
#                 "First_In":          checkin_time,
#                 "Worker_Full_Name":  full_name,
#             }}
#         )
#         if r and r.status_code in (200, 201):
#             mark_checked_in(zk_key, checkin_time)
#             return True, f"[OK] {full_name} checked IN at {now.strftime('%H:%M')}"
#         err = r.text if r else "No response"
#         return False, (
#             f"[ERROR] Check-in failed "
#             f"(HTTP {r.status_code if r else '???'}): {err}"
#         )

#     # ----------------------------------------------------------
#     # CHECK-OUT
#     # ----------------------------------------------------------
#     elif action == "checkout":
#         if is_checked_out_today(zk_key):
#             t = load_checkin_lock().get("checked_out", {}).get(zk_key, "N/A")
#             return False, (
#                 f"{full_name} already checked OUT today at {t}. "
#                 "Only one check-in/out cycle is allowed per day."
#             )

#         checkin_time = is_checked_in_today(zk_key)
#         if not checkin_time:
#             return False, (
#                 f"{full_name} has not checked IN yet today. "
#                 "Please check IN first."
#             )

#         # Calculate hours worked
#         try:
#             first_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             first_dt = now
#         total_secs     = (now - first_dt).total_seconds()
#         total_hours    = total_secs / 3600
#         total_time_str = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

#         # ----------------------------------------------------------
#         # FIX: Resolve auth token ONCE before all GET/PATCH calls.
#         # Previously auth_headers() was called inside do_patch() which
#         # triggered a fresh token request on every attempt, adding
#         # latency and sometimes causing cascading timeouts.
#         # ----------------------------------------------------------
#         hdrs = auth_headers()

#         report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#         records    = []

#         # Strategy A: lookup ID + ISO date
#         crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_iso}")'
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if r and r.status_code == 200:
#             records = r.json().get("data", [])

#         # Strategy B: lookup ID + display date
#         if not records:
#             crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_display}")'
#             r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#             if r and r.status_code == 200:
#                 records = r.json().get("data", [])

#         # Strategy C: worker only, match date in Python
#         if not records:
#             crit = f'(Worker_Name.ID == "{worker_id}")'
#             r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if str(rec.get("Date_field", "")).strip() in possible
#                 ]

#         # Strategy D: no filter, match worker ID + date in Python
#         if not records:
#             r = zoho_request("GET", report_url, headers=hdrs)
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if rec.get("Worker_Name", {}).get("ID") == worker_id
#                     and str(rec.get("Date_field", "")).strip() in possible
#                 ]

#         if not records:
#             return False, (
#                 f"[ERROR] Check-out failed: attendance record not found.\n"
#                 f"   Worker Zoho ID : {worker_id}\n"
#                 f"   Dates tried    : {today_display} / {today_iso} / {today_mmdd}"
#             )

#         att_id = records[0]["ID"]

#         # Fetch the single record to discover real field names
#         single_url = f"{report_url}/{att_id}"
#         r_rec = zoho_request("GET", single_url, headers=hdrs)
#         rec_data = {}
#         if r_rec and r_rec.status_code == 200:
#             payload = r_rec.json()
#             raw = payload.get("data", payload)
#             if isinstance(raw, list) and raw:
#                 rec_data = raw[0]
#             elif isinstance(raw, dict):
#                 rec_data = raw

#         last_out_val  = now.strftime("%d-%b-%Y %H:%M:%S")
#         total_hrs_val = round(total_hours, 4)

#         update_payload = {
#             "Last_Out":    last_out_val,
#             "Total_Hours": total_hrs_val,
#         }

#         form_update_url   = f"{form_url}/{att_id}"
#         report_update_url = f"{report_url}/{att_id}"

#         # ----------------------------------------------------------
#         # Multi-strategy update: Zoho Creator v2 behaviour varies by
#         # tenant — try every known-working combination in order.
#         #
#         # Strategy 1: PATCH report  — form-encoded  data=<json-str>
#         # Strategy 2: PATCH form    — form-encoded  data=<json-str>
#         # Strategy 3: PATCH report  — JSON body     json={"data":{}}
#         # Strategy 4: PATCH form    — JSON body     json={"data":{}}
#         # Strategy 5: PUT  report   — form-encoded  data=<json-str>
#         # Strategy 6: PUT  form     — form-encoded  data=<json-str>
#         # ----------------------------------------------------------
#         update_strategies = [
#             ("PATCH", report_update_url, {"data": {"data": json.dumps(update_payload)}}),
#             ("PATCH", form_update_url,   {"data": {"data": json.dumps(update_payload)}}),
#             ("PATCH", report_update_url, {"json": {"data": update_payload}}),
#             ("PATCH", form_update_url,   {"json": {"data": update_payload}}),
#             ("PUT",   report_update_url, {"data": {"data": json.dumps(update_payload)}}),
#             ("PUT",   form_update_url,   {"data": {"data": json.dumps(update_payload)}}),
#         ]

#         r2        = None
#         debug_log = []
#         for method, url, body_kwargs in update_strategies:
#             endpoint  = "form" if "/form/" in url else "report"
#             body_type = "json" if "json" in body_kwargs else "form-enc"
#             r2 = zoho_request(
#                 method, url,
#                 headers=hdrs,
#                 retries=1,
#                 timeout=PATCH_TIMEOUT,
#                 **body_kwargs,
#             )
#             status  = r2.status_code if r2 else "timeout"
#             snippet = (r2.text[:80] if r2 and r2.text else "")
#             debug_log.append(f"{method} {endpoint} ({body_type}) -> {status}  {snippet}")
#             if r2 and r2.status_code in (200, 201):
#                 break
#             time.sleep(1)

#         if r2 and r2.status_code in (200, 201):
#             mark_checked_out(zk_key)
#             return True, (
#                 f"[OK] {full_name} checked OUT at {now.strftime('%H:%M')} "
#                 f"| Total: {total_time_str}"
#             )

#         err       = r2.text[:300] if r2 else "No response (timeout)"
#         debug_str = "\n   ".join(debug_log)
#         return False, (
#             f"[ERROR] Check-out failed (all strategies exhausted)\n"
#             f"   Record ID  : {att_id}\n"
#             f"   Payload    : {json.dumps(update_payload)}\n"
#             f"   Attempts:\n   {debug_str}\n"
#             f"   Last resp  : {err}"
#         )

#     return False, "[ERROR] Unknown action"


# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root  = root
#         self.root.title("Zoho Attendance Fingerprint System")
#         self.root.geometry("640x560")
#         self._busy = False
#         self._build_ui()

#     def _build_ui(self):
#         hdr = tk.Frame(self.root, bg="#2c3e50", pady=12)
#         hdr.pack(fill=tk.X)
#         tk.Label(hdr, text="Zoho Attendance System",
#                  font=("Arial", 15, "bold"),
#                  bg="#2c3e50", fg="white").pack()

#         inp = tk.Frame(self.root, pady=12)
#         inp.pack()
#         tk.Label(inp, text="User ID:", font=("Arial", 12)).pack(
#             side=tk.LEFT, padx=6)
#         self.user_entry = tk.Entry(inp, font=("Arial", 13), width=18)
#         self.user_entry.pack(side=tk.LEFT, padx=6)
#         self.user_entry.bind("<KeyRelease>", self._on_id_change)
#         self.user_entry.focus_set()

#         self.status_lbl = tk.Label(
#             self.root, text="Enter a User ID to begin.",
#             font=("Arial", 10, "italic"), fg="gray")
#         self.status_lbl.pack(pady=4)

#         btn_frame = tk.Frame(self.root, pady=6)
#         btn_frame.pack()

#         self.btn_in = tk.Button(
#             btn_frame, text="Check-In", width=16,
#             font=("Arial", 11, "bold"),
#             bg="#28a745", fg="white",
#             activebackground="#1e7e34",
#             disabledforeground="#999999",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkin")
#         )
#         self.btn_in.pack(side=tk.LEFT, padx=14, ipady=6)

#         self.btn_out = tk.Button(
#             btn_frame, text="Check-Out", width=16,
#             font=("Arial", 11, "bold"),
#             bg="#dc3545", fg="white",
#             activebackground="#bd2130",
#             disabledforeground="#999999",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkout")
#         )
#         self.btn_out.pack(side=tk.LEFT, padx=14, ipady=6)

#         tk.Frame(self.root, height=1, bg="#cccccc").pack(
#             fill=tk.X, pady=6, padx=10)

#         tk.Label(self.root, text="Activity Log:",
#                  font=("Arial", 11, "bold")).pack(anchor="w", padx=14)
#         log_frame = tk.Frame(self.root)
#         log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
#         sb = tk.Scrollbar(log_frame)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(
#             log_frame, height=14, width=74,
#             font=("Courier", 10),
#             yscrollcommand=sb.set,
#             state=tk.DISABLED
#         )
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#     def log(self, msg):
#         def _do():
#             ts = datetime.now().strftime("%H:%M:%S")
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{ts}]  {msg}\n")
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _set_status(self, text, color="gray"):
#         self.root.after(
#             0, lambda: self.status_lbl.config(text=text, fg=color))

#     def _set_buttons(self, in_state, out_state):
#         def _do():
#             self.btn_in.config(state=in_state)
#             self.btn_out.config(state=out_state)
#         self.root.after(0, _do)

#     def _apply_status_ui(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "Attendance complete for today - no further action allowed.",
#                 "red")
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status(
#                 "Already checked IN today - Check-Out is now available.",
#                 "darkorange")
#         else:
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status(
#                 "Not yet checked in today - Check-In is available.",
#                 "darkgreen")

#     def _on_id_change(self, _event=None):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Enter a User ID to begin.", "gray")
#             return
#         self._apply_status_ui(get_worker_status(uid))

#     def _trigger(self, action):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         threading.Thread(
#             target=self._process, args=(uid, action), daemon=True
#         ).start()

#     def _process(self, zk_user_id, action):
#         zk          = None
#         device_open = False
#         try:
#             zk = ZKFP2()
#             zk.Init()
#             if zk.GetDeviceCount() == 0:
#                 self.log("No fingerprint device found.")
#                 return
#             zk.OpenDevice(0)
#             device_open = True

#             time.sleep(1)
#             self.log("Place your finger on the scanner...")

#             capture  = None
#             max_wait = 30
#             waited   = 0.0
#             last_dot = 0

#             while not capture:
#                 capture = zk.AcquireFingerprint()
#                 if not capture:
#                     time.sleep(0.2)
#                     waited += 0.2
#                     if int(waited) > last_dot and int(waited) % 3 == 0:
#                         self.log(f"  Waiting for finger... ({int(waited)}s)")
#                         last_dot = int(waited)
#                     if waited >= max_wait:
#                         self.log("Fingerprint timeout - please try again.")
#                         return

#             tmp, img = capture
#             self.log("Fingerprint captured successfully.")

#             self.log("Looking up worker...")
#             worker = find_worker(zk_user_id)
#             if not worker:
#                 self.log("Worker not found in Zoho.")
#                 return

#             full_name      = worker.get("Full_Name", "N/A")
#             zoho_worker_id = worker["ID"]

#             status = get_worker_status(zk_user_id)
#             if status == "done":
#                 self.log(
#                     f"{full_name} has already completed attendance today. "
#                     "No further action until tomorrow.")
#                 self._apply_status_ui(status)
#                 return
#             if status == "checked_in" and action == "checkin":
#                 t = is_checked_in_today(zk_user_id)
#                 self.log(
#                     f"{full_name} already checked IN at "
#                     f"{t.split(' ')[-1] if t else 'N/A'} today. "
#                     "Use Check-Out instead.")
#                 self._apply_status_ui(status)
#                 return
#             if status == "none" and action == "checkout":
#                 self.log(
#                     f"{full_name} has not checked IN yet today. "
#                     "Please check IN first.")
#                 self._apply_status_ui(status)
#                 return

#             project_id = (
#                 worker.get("Projects_Assigned", {}).get("ID")
#                 or DEFAULT_PROJECT_ID
#             )
#             success, message = log_attendance(
#                 zoho_worker_id, zk_user_id, project_id, full_name, action
#             )
#             self.log(message)

#             if success:
#                 self._apply_status_ui(get_worker_status(zk_user_id))

#         except Exception as exc:
#             self.log(f"ERROR: {exc}")

#         finally:
#             if zk and device_open:
#                 try:
#                     zk.CloseDevice()
#                     zk.Terminate()
#                 except Exception:
#                     pass
#             self._busy = False

#             def _reset():
#                 self.user_entry.delete(0, tk.END)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status("Enter a User ID to begin.", "gray")
#                 self.log("-" * 50 + "\nReady for next user.")
#             self.root.after(0, _reset)


# # ===========================================================
# # MAIN
# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop()




# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import font as tkfont

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"
# MAX_RETRIES        = 3
# RETRY_DELAY        = 2
# TIMEOUT            = 45
# PATCH_TIMEOUT      = 60
# RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# # ===========================================================
# # NETWORK HELPER
# # ===========================================================
# def zoho_request(method, url, *, retries=MAX_RETRIES,
#                  expected_statuses=(200, 201), timeout=None, **kwargs):
#     kwargs.setdefault("timeout", timeout or TIMEOUT)
#     for attempt in range(1, retries + 1):
#         try:
#             resp = requests.request(method, url, **kwargs)
#             if resp.status_code in expected_statuses:
#                 return resp
#             if resp.status_code in RETRYABLE_STATUSES:
#                 time.sleep(RETRY_DELAY * attempt)
#                 continue
#             return resp
#         except (requests.exceptions.ConnectionError,
#                 requests.exceptions.Timeout, OSError):
#             if attempt == retries:
#                 return None
#             time.sleep(RETRY_DELAY * attempt)
#     return None

# # ===========================================================
# # CHECKIN LOCK (local JSON state)
# # ===========================================================
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

# def is_checked_in_today(zk_user_id):
#     return load_checkin_lock()["checked_in"].get(str(zk_user_id))

# def is_checked_out_today(zk_user_id):
#     return str(zk_user_id) in load_checkin_lock().get("checked_out", {})

# def mark_checked_in(zk_user_id, time_str):
#     lock = load_checkin_lock()
#     lock["checked_in"][str(zk_user_id)] = time_str
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def mark_checked_out(zk_user_id):
#     lock = load_checkin_lock()
#     lock["checked_in"].pop(str(zk_user_id), None)
#     lock.setdefault("checked_out", {})[str(zk_user_id)] = \
#         datetime.now().strftime("%H:%M:%S")
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(lock, f)

# def get_worker_status(zk_user_id):
#     key = str(zk_user_id)
#     if is_checked_out_today(key):
#         return "done"
#     if is_checked_in_today(key):
#         return "checked_in"
#     return "none"

# # ===========================================================
# # AUTHENTICATION
# # ===========================================================
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
#     r = zoho_request("POST", url, data=data, timeout=30)
#     if r:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     if not token:
#         raise RuntimeError("Could not obtain Zoho access token.")
#     return {"Authorization": f"Zoho-oauthtoken {token}"}

# # ===========================================================
# # WORKER LOOKUP
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(),
#                      params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         if data:
#             return data[0]
#     return None

# # ===========================================================
# # ATTENDANCE - CHECK-IN & CHECK-OUT
# # ===========================================================
# def log_attendance(worker_id, zk_user_id, project_id, full_name, action):
#     now      = datetime.now()
#     form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#     zk_key   = str(zk_user_id)

#     today_display = now.strftime("%d-%b-%Y")   # e.g. 21-Feb-2025
#     today_iso     = now.strftime("%Y-%m-%d")   # e.g. 2025-02-21
#     today_mmdd    = now.strftime("%m/%d/%Y")   # e.g. 02/21/2025

#     # ── CHECK-IN ──────────────────────────────────────────
#     if action == "checkin":
#         if is_checked_out_today(zk_key):
#             return False, (
#                 f"{full_name} has already completed attendance for today.\n"
#                 "Only one check-in/out cycle is allowed per day."
#             )
#         if is_checked_in_today(zk_key):
#             t = is_checked_in_today(zk_key)
#             return False, (
#                 f"{full_name} already checked IN today at "
#                 f"{t.split(' ')[-1] if t else 'N/A'}.\n"
#                 "Please use Check-Out instead."
#             )

#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         hdrs = auth_headers()
#         r = zoho_request(
#             "POST", form_url,
#             headers=hdrs,
#             json={"data": {
#                 "Worker_ID_Lookup":  worker_id,
#                 "Worker_Name":       worker_id,
#                 "Projects":          project_id,
#                 "Projects_Assigned": project_id,
#                 "Date":              today_display,
#                 "First_In":          checkin_time,
#                 "Worker_Full_Name":  full_name,
#             }}
#         )
#         if r and r.status_code in (200, 201):
#             mark_checked_in(zk_key, checkin_time)
#             return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
#         err = r.text if r else "No response"
#         return False, (
#             f" Check-in failed "
#             f"(HTTP {r.status_code if r else '???'}): {err}"
#         )

#     # ── CHECK-OUT ─────────────────────────────────────────
#     elif action == "checkout":
#         if is_checked_out_today(zk_key):
#             t = load_checkin_lock().get("checked_out", {}).get(zk_key, "N/A")
#             return False, (
#                 f"{full_name} already checked OUT today at {t}.\n"
#                 "Only one check-in/out cycle is allowed per day."
#             )

#         checkin_time = is_checked_in_today(zk_key)
#         if not checkin_time:
#             return False, (
#                 f"{full_name} has not checked IN yet today.\n"
#                 "Please check IN first."
#             )

#         # Calculate hours worked
#         try:
#             first_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             first_dt = now
#         total_secs     = (now - first_dt).total_seconds()
#         total_hours    = total_secs / 3600
#         total_time_str = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

#         hdrs       = auth_headers()   # resolve token ONCE
#         report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#         records    = []

#         # Strategy A: Worker_ID_Lookup + Date  (same as working CLI)
#         crit = f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")'
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if r and r.status_code == 200:
#             records = r.json().get("data", [])

#         # Strategy B: Worker_Name.ID + Date
#         if not records:
#             crit = f'(Worker_Name.ID == "{worker_id}" && Date == "{today_display}")'
#             r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#             if r and r.status_code == 200:
#                 records = r.json().get("data", [])

#         # Strategy C: Worker_ID_Lookup only, filter date in Python
#         if not records:
#             crit = f'(Worker_ID_Lookup == "{worker_id}")'
#             r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if str(rec.get("Date", "")).strip() in possible
#                 ]

#         # Strategy D: no filter, match worker + date in Python
#         if not records:
#             r = zoho_request("GET", report_url, headers=hdrs)
#             if r and r.status_code == 200:
#                 raw      = r.json().get("data", [])
#                 possible = {today_display, today_iso, today_mmdd}
#                 records  = [
#                     rec for rec in raw
#                     if rec.get("Worker_ID_Lookup") == worker_id
#                     and str(rec.get("Date", "")).strip() in possible
#                 ]

#         if not records:
#             return False, (
#                 f" Check-out failed: attendance record not found.\n"
#                 f"   Worker Zoho ID : {worker_id}\n"
#                 f"   Date tried     : {today_display}"
#             )

#         att_id     = records[0]["ID"]
#         update_url = f"{form_url}/{att_id}"

#         last_out_val  = now.strftime("%d-%b-%Y %H:%M:%S")
#         total_hrs_val = round(total_hours, 4)

#         # Single PUT to form/{att_id} — matches working CLI pattern exactly
#         r2 = zoho_request(
#             "PUT", update_url,
#             headers=hdrs,
#             json={"data": {
#                 "Last_Out":    last_out_val,
#                 "Total_Hours": total_hrs_val,
#             }},
#             timeout=PATCH_TIMEOUT,
#         )

#         if r2 and r2.status_code in (200, 201):
#             mark_checked_out(zk_key)
#             return True, (
#                 f"🚪  {full_name} checked OUT at {now.strftime('%H:%M')}\n"
#                 f"    Total time worked: {total_time_str}"
#             )

#         err = r2.text[:300] if r2 else "No response (timeout)"
#         return False, (
#             f" Check-out failed (HTTP {r2.status_code if r2 else '???'})\n"
#             f"   Record ID : {att_id}\n"
#             f"   Response  : {err}"
#         )

#     return False, "  Unknown action"


# # ===========================================================
# # COLOURS & FONTS
# # ===========================================================
# BG        = "#0f1117"
# CARD      = "#1a1d27"
# BORDER    = "#2a2d3e"
# ACCENT    = "#4f8ef7"
# GREEN     = "#22c55e"
# RED       = "#ef4444"
# ORANGE    = "#f59e0b"
# TEXT      = "#e2e8f0"
# MUTED     = "#64748b"
# WHITE     = "#ffffff"
# SUCCESS_BG = "#052e16"
# ERROR_BG   = "#1c0a0a"
# INFO_BG    = "#0c1a3a"


# # ===========================================================
# # GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root  = root
#         self.root.title("Zoho Attendance System")
#         self.root.geometry("720x680")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy = False
#         self._clock_after = None
#         self._build_ui()
#         self._tick_clock()

#     # ── UI CONSTRUCTION ───────────────────────────────────
#     def _build_ui(self):
#         # ── TOP HEADER ──────────────────────────────────
#         hdr = tk.Frame(self.root, bg=CARD, pady=0)
#         hdr.pack(fill=tk.X)

#         # thin accent bar at top
#         accent_bar = tk.Frame(hdr, bg=ACCENT, height=3)
#         accent_bar.pack(fill=tk.X)

#         inner_hdr = tk.Frame(hdr, bg=CARD, padx=24, pady=14)
#         inner_hdr.pack(fill=tk.X)

#         left_hdr = tk.Frame(inner_hdr, bg=CARD)
#         left_hdr.pack(side=tk.LEFT, fill=tk.Y)

#         tk.Label(left_hdr, text="ZOHO ATTENDANCE",
#                  font=("Courier", 13, "bold"),
#                  bg=CARD, fg=ACCENT).pack(anchor="w")
#         tk.Label(left_hdr, text="Fingerprint Check-In / Check-Out System",
#                  font=("Courier", 9),
#                  bg=CARD, fg=MUTED).pack(anchor="w")

#         right_hdr = tk.Frame(inner_hdr, bg=CARD)
#         right_hdr.pack(side=tk.RIGHT, fill=tk.Y)

#         self.date_lbl = tk.Label(right_hdr,
#                  text=datetime.now().strftime("%A, %d %b %Y"),
#                  font=("Courier", 9), bg=CARD, fg=MUTED)
#         self.date_lbl.pack(anchor="e")
#         self.clock_lbl = tk.Label(right_hdr, text="",
#                  font=("Courier", 18, "bold"), bg=CARD, fg=TEXT)
#         self.clock_lbl.pack(anchor="e")

#         # separator
#         tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

#         # ── MAIN BODY ────────────────────────────────────
#         body = tk.Frame(self.root, bg=BG, padx=28, pady=18)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ── ID ENTRY CARD ────────────────────────────────
#         id_card = tk.Frame(body, bg=CARD, bd=0,
#                            highlightbackground=BORDER,
#                            highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 14))

#         id_inner = tk.Frame(id_card, bg=CARD, padx=18, pady=14)
#         id_inner.pack(fill=tk.X)

#         tk.Label(id_inner, text="WORKER ID",
#                  font=("Courier", 8, "bold"),
#                  bg=CARD, fg=MUTED).pack(anchor="w")

#         entry_row = tk.Frame(id_inner, bg=CARD)
#         entry_row.pack(fill=tk.X, pady=(4, 0))

#         # styled entry
#         entry_border = tk.Frame(entry_row, bg=ACCENT, padx=1, pady=1)
#         entry_border.pack(side=tk.LEFT, fill=tk.Y)

#         entry_inner = tk.Frame(entry_border, bg="#1e2130")
#         entry_inner.pack()

#         self.user_entry = tk.Entry(
#             entry_inner,
#             font=("Courier", 20, "bold"),
#             width=14, bd=0,
#             bg="#1e2130", fg=WHITE,
#             insertbackground=ACCENT,
#             selectbackground=ACCENT,
#         )
#         self.user_entry.pack(padx=10, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_id_change)
#         self.user_entry.bind("<Return>", self._on_enter)
#         self.user_entry.focus_set()

#         # worker name display
#         self.worker_lbl = tk.Label(
#             entry_row, text="",
#             font=("Courier", 11), bg=CARD, fg=MUTED)
#         self.worker_lbl.pack(side=tk.LEFT, padx=16)

#         # ── STATUS BADGE ─────────────────────────────────
#         self.status_frame = tk.Frame(body, bg=INFO_BG,
#                                      highlightbackground=ACCENT,
#                                      highlightthickness=1)
#         self.status_frame.pack(fill=tk.X, pady=(0, 14))

#         self.status_lbl = tk.Label(
#             self.status_frame,
#             text="◉  Enter a Worker ID to begin",
#             font=("Courier", 10),
#             bg=INFO_BG, fg=ACCENT,
#             padx=14, pady=10, anchor="w")
#         self.status_lbl.pack(fill=tk.X)

#         # ── ACTION BUTTONS ────────────────────────────────
#         btn_row = tk.Frame(body, bg=BG)
#         btn_row.pack(fill=tk.X, pady=(0, 14))

#         self.btn_in = tk.Button(
#             btn_row,
#             text="▶  CHECK  IN",
#             font=("Courier", 12, "bold"),
#             width=18,
#             bg=GREEN, fg=BG,
#             activebackground="#16a34a",
#             activeforeground=WHITE,
#             relief=tk.FLAT, cursor="hand2",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkin")
#         )
#         self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0, 10))

#         self.btn_out = tk.Button(
#             btn_row,
#             text="◼  CHECK  OUT",
#             font=("Courier", 12, "bold"),
#             width=18,
#             bg=RED, fg=WHITE,
#             activebackground="#b91c1c",
#             activeforeground=WHITE,
#             relief=tk.FLAT, cursor="hand2",
#             state=tk.DISABLED,
#             command=lambda: self._trigger("checkout")
#         )
#         self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0, 10))

#         # clear button
#         self.btn_clear = tk.Button(
#             btn_row,
#             text="✕",
#             font=("Courier", 12, "bold"),
#             width=4,
#             bg=BORDER, fg=MUTED,
#             activebackground=MUTED,
#             activeforeground=WHITE,
#             relief=tk.FLAT, cursor="hand2",
#             command=self._clear_entry
#         )
#         self.btn_clear.pack(side=tk.LEFT, ipady=10)

#         # ── ACTIVITY LOG ─────────────────────────────────
#         log_header = tk.Frame(body, bg=BG)
#         log_header.pack(fill=tk.X, pady=(4, 6))
#         tk.Label(log_header, text="ACTIVITY LOG",
#                  font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         self.btn_cls_log = tk.Button(
#             log_header, text="CLEAR",
#             font=("Courier", 7, "bold"),
#             bg=BORDER, fg=MUTED,
#             activebackground=MUTED,
#             activeforeground=WHITE,
#             relief=tk.FLAT, cursor="hand2",
#             padx=6, pady=1,
#             command=self._clear_log
#         )
#         self.btn_cls_log.pack(side=tk.RIGHT)

#         log_wrap = tk.Frame(body, bg=CARD,
#                             highlightbackground=BORDER,
#                             highlightthickness=1)
#         log_wrap.pack(fill=tk.BOTH, expand=True)

#         sb = tk.Scrollbar(log_wrap, bg=BORDER, troughcolor=CARD,
#                           activebackground=ACCENT)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)

#         self.log_box = tk.Text(
#             log_wrap,
#             font=("Courier", 10),
#             bg=CARD, fg=TEXT,
#             insertbackground=ACCENT,
#             selectbackground=ACCENT,
#             relief=tk.FLAT,
#             padx=12, pady=10,
#             yscrollcommand=sb.set,
#             state=tk.DISABLED,
#         )
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#         # text colour tags
#         self.log_box.tag_config("ok",      foreground=GREEN)
#         self.log_box.tag_config("err",     foreground=RED)
#         self.log_box.tag_config("warn",    foreground=ORANGE)
#         self.log_box.tag_config("info",    foreground=ACCENT)
#         self.log_box.tag_config("ts",      foreground=MUTED)
#         self.log_box.tag_config("divider", foreground=BORDER)

#         # ── FOOTER ───────────────────────────────────────
#         footer = tk.Frame(self.root, bg=CARD, pady=5)
#         footer.pack(fill=tk.X, side=tk.BOTTOM)
#         tk.Label(footer,
#                  text="Wavemark Properties Limited  ·  Powered by ZKTeco + Zoho Creator",
#                  font=("Courier", 7), bg=CARD, fg=MUTED).pack()

#     # ── CLOCK ─────────────────────────────────────────────
#     def _tick_clock(self):
#         now = datetime.now()
#         self.clock_lbl.config(text=now.strftime("%H:%M:%S"))
#         self.date_lbl.config(text=now.strftime("%A, %d %b %Y"))
#         self._clock_after = self.root.after(1000, self._tick_clock)

#     # ── LOGGING ───────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             ts = datetime.now().strftime("%H:%M:%S")
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{ts}]  ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _log_divider(self):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END,
#                 "─" * 60 + "\n", "divider")
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     # ── STATUS BADGE ──────────────────────────────────────
#     def _set_status(self, text, color=ACCENT, bg=INFO_BG, border=ACCENT):
#         def _do():
#             self.status_frame.config(highlightbackground=border)
#             self.status_frame.config(bg=bg)
#             self.status_lbl.config(text=text, fg=color, bg=bg)
#         self.root.after(0, _do)

#     def _set_buttons(self, in_state, out_state):
#         def _do():
#             self.btn_in.config(state=in_state,
#                 bg=GREEN if in_state == tk.NORMAL else "#1a3a2a",
#                 fg=BG   if in_state == tk.NORMAL else MUTED)
#             self.btn_out.config(state=out_state,
#                 bg=RED  if out_state == tk.NORMAL else "#3a1a1a",
#                 fg=WHITE if out_state == tk.NORMAL else MUTED)
#         self.root.after(0, _do)

#     def _apply_status_ui(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "◉  Attendance complete for today — no further action until tomorrow.",
#                 RED, ERROR_BG, RED)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status(
#                 "◉  Worker is CHECKED IN — Check-Out is now available.",
#                 ORANGE, "#1c1200", ORANGE)
#         else:
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status(
#                 "◉  Not yet checked in today — Check-In is available.",
#                 GREEN, SUCCESS_BG, GREEN)

#     def _set_worker_label(self, name="", color=MUTED):
#         self.root.after(0, lambda: self.worker_lbl.config(text=name, fg=color))

#     # ── ID ENTRY EVENTS ───────────────────────────────────
#     def _on_id_change(self, _event=None):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("◉  Enter a Worker ID to begin.",
#                              ACCENT, INFO_BG, ACCENT)
#             self._set_worker_label("")
#             return
#         self._apply_status_ui(get_worker_status(uid))

#     def _on_enter(self, _event=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy:
#             return
#         status = get_worker_status(uid)
#         if status == "none":
#             self._trigger("checkin")
#         elif status == "checked_in":
#             self._trigger("checkout")

#     def _clear_entry(self):
#         self.user_entry.delete(0, tk.END)
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉  Enter a Worker ID to begin.",
#                          ACCENT, INFO_BG, ACCENT)
#         self._set_worker_label("")
#         self.user_entry.focus_set()

#     # ── TRIGGER ACTION ────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         threading.Thread(
#             target=self._process, args=(uid, action), daemon=True
#         ).start()

#     # ── BACKGROUND WORKER THREAD ──────────────────────────
#     def _process(self, zk_user_id, action):
#         zk          = None
#         device_open = False
#         action_label = "CHECK-IN" if action == "checkin" else "CHECK-OUT"

#         try:
#             self._log_divider()
#             self.log(f"Starting {action_label} for ID: {zk_user_id}", "info")

#             # ── Init fingerprint device ──────────────────
#             zk = ZKFP2()
#             zk.Init()
#             if zk.GetDeviceCount() == 0:
#                 self.log("No fingerprint device detected. Connect scanner and retry.", "err")
#                 return
#             zk.OpenDevice(0)
#             device_open = True

#             self.log("Scanner ready — place your finger on the sensor...", "info")
#             self._set_status("◉  Waiting for fingerprint scan...",
#                              ORANGE, "#1c1200", ORANGE)

#             # ── Capture fingerprint ──────────────────────
#             capture  = None
#             max_wait = 30
#             waited   = 0.0
#             last_dot = 0

#             while not capture:
#                 capture = zk.AcquireFingerprint()
#                 if not capture:
#                     time.sleep(0.2)
#                     waited += 0.2
#                     if int(waited) > last_dot and int(waited) % 5 == 0:
#                         self.log(f"  Waiting for finger... ({int(waited)}s elapsed)", "warn")
#                         last_dot = int(waited)
#                     if waited >= max_wait:
#                         self.log("Fingerprint scan timed out (30s). Please try again.", "err")
#                         return

#             self.log("Fingerprint captured successfully.", "ok")

#             # ── Lookup worker in Zoho ────────────────────
#             self.log("Looking up worker in Zoho...", "info")
#             self._set_status("◉  Querying Zoho — please wait...",
#                              ACCENT, INFO_BG, ACCENT)
#             worker = find_worker(zk_user_id)
#             if not worker:
#                 self.log(
#                     f"Worker ID '{zk_user_id}' not found in Zoho. "
#                     "Check the ID or contact admin.", "err")
#                 return

#             full_name      = worker.get("Full_Name", "N/A")
#             zoho_worker_id = worker["ID"]
#             self._set_worker_label(full_name, GREEN)
#             self.log(f"Worker found: {full_name}", "ok")

#             # ── Guard: re-check status after Zoho lookup ─
#             status = get_worker_status(zk_user_id)
#             if status == "done":
#                 self.log(
#                     f"{full_name} has already completed attendance today. "
#                     "See you tomorrow!", "warn")
#                 self._apply_status_ui(status)
#                 return
#             if status == "checked_in" and action == "checkin":
#                 t = is_checked_in_today(zk_user_id)
#                 self.log(
#                     f"{full_name} already checked IN at "
#                     f"{t.split(' ')[-1] if t else 'N/A'} today. "
#                     "Use Check-Out.", "warn")
#                 self._apply_status_ui(status)
#                 return
#             if status == "none" and action == "checkout":
#                 self.log(
#                     f"{full_name} has not checked IN yet today. "
#                     "Please check IN first.", "warn")
#                 self._apply_status_ui(status)
#                 return

#             # ── Resolve project ──────────────────────────
#             project_id = (
#                 worker.get("Projects_Assigned", {}).get("ID")
#                 or DEFAULT_PROJECT_ID
#             )

#             # ── Post to Zoho ─────────────────────────────
#             self.log(f"Posting {action_label} to Zoho Creator...", "info")
#             success, message = log_attendance(
#                 zoho_worker_id, zk_user_id, project_id, full_name, action
#             )

#             tag = "ok" if success else "err"
#             for line in message.splitlines():
#                 if line.strip():
#                     self.log(line.strip(), tag)

#             if success:
#                 self._apply_status_ui(get_worker_status(zk_user_id))
#             else:
#                 # restore correct button states
#                 self._apply_status_ui(status)

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")

#         finally:
#             if zk and device_open:
#                 try:
#                     zk.CloseDevice()
#                     zk.Terminate()
#                 except Exception:
#                     pass
#             self._busy = False

#             def _reset():
#                 self.user_entry.delete(0, tk.END)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status("◉  Enter a Worker ID to begin.",
#                                  ACCENT, INFO_BG, ACCENT)
#                 self._set_worker_label("")
#                 self.log("─" * 60 + "  Ready for next worker.", "ts")
#                 self.user_entry.focus_set()
#             self.root.after(0, _reset)


# # ===========================================================
# # MAIN
# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()

#     # Centre window on screen
#     root.update_idletasks()
#     w, h = 720, 680
#     x = (root.winfo_screenwidth()  - w) // 2
#     y = (root.winfo_screenheight() - h) // 2
#     root.geometry(f"{w}x{h}+{x}+{y}")

#     app = FingerprintGUI(root)
#     root.mainloop()



# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ===========================================================
# # GLOBAL SDK INITIALIZATION
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     try:
#         return requests.request(method, url, **kwargs)
#     except Exception as e:
#         return None

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
#     if r and r.status_code == 200:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE MANAGEMENT
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#                 if data.get("date") == today: return data
#         except: pass
#     return {"date": today, "checked_in": {}, "checked_out": {}}

# def save_lock(data):
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(data, f)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     if str(zk_id) in lock["checked_out"]: return "done"
#     if str(zk_id) in lock["checked_in"]: return "checked_in"
#     return "none"

# # ===========================================================
# # ZOHO API LOGIC
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def log_attendance(worker_id, zk_id, project_id, full_name, action):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")
    
#     # ── CHECK-IN ──────────────────────────────────────────
#     if action == "checkin":
#         form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
        
#         payload = {
#             "data": {
#                 "Worker_Name":       worker_id,
#                 "Projects":          project_id,
#                 "Date":              today_display,
#                 "First_In":          checkin_time,
#                 "Worker_Full_Name":  full_name,
#             }
#         }
        
#         r = zoho_request("POST", form_url, headers=auth_headers(), json=payload)
#         if r and r.status_code in (200, 201):
#             zoho_rec_id = r.json().get("data", {}).get("ID")
#             lock = load_lock()
#             lock["checked_in"][zk_key] = {"time": checkin_time, "zoho_id": zoho_rec_id}
#             save_lock(lock)
#             return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
        
#         return False, f"Check-in failed: {r.text if r else 'Timeout'}"

#     # ── CHECK-OUT ─────────────────────────────────────────
#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info: return False, "Local check-in record not found."

#         att_record_id = info.get("zoho_id")
        
#         # Fallback Search if ID is missing from local JSON
#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             # Lookup criteria: No quotes for the ID number
#             crit = f'(Worker_Name == {worker_id} && Date == "{today_iso}")'
#             r_s = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#             if r_s and r_s.status_code == 200 and r_s.json().get("data"):
#                 att_record_id = r_s.json()["data"][0]["ID"]

#         if not att_record_id:
#             return False, "Could not locate the Zoho Record ID for update."

#         # Calculate Hours
#         try:
#             dt_in = datetime.strptime(info["time"], "%d-%b-%Y %H:%M:%S")
#         except:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)

#         # Correct Update Strategy: PATCH to the Report URI
#         update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}/{att_record_id}"
        
#         r_u = zoho_request(
#             "PATCH", update_url, 
#             headers=auth_headers(),
#             json={"data": {
#                 "Last_Out":    now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Total_Hours": round(total_hours, 4)
#             }}
#         )

#         if r_u and r_u.status_code == 200:
#             res_body = r_u.json()
#             if res_body.get("code") == 3000: # 3000 = Zoho Success Code
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = now.strftime("%H:%M:%S")
#                 save_lock(lock)
#                 return True, f"🚪  {full_name} checked OUT. Worked: {round(total_hours, 2)} hrs"
#             else:
#                 return False, f"Zoho Error: {res_body.get('message')}"

#         return False, f"Check-out failed (HTTP {r_u.status_code if r_u else 'Timeout'})"

#     return False, "Unknown action"

# # ===========================================================
# # GUI
# # ===========================================================
# BG, CARD, ACCENT, GREEN, RED, ORANGE = "#0f1117", "#1a1d27", "#4f8ef7", "#22c55e", "#ef4444", "#f59e0b"

# class FingerprintGUI:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Zoho Attendance System")
#         self.root.geometry("720x680")
#         self.root.configure(bg=BG)
#         self._busy = False
#         self._build_ui()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     def _build_ui(self):
#         hdr = tk.Frame(self.root, bg=CARD); hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=ACCENT, height=3).pack(fill=tk.X)
#         ih = tk.Frame(hdr, bg=CARD, padx=20, pady=15); ih.pack(fill=tk.X)
#         tk.Label(ih, text="ZOHO ATTENDANCE", font=("Courier", 14, "bold"), bg=CARD, fg=ACCENT).pack(side=tk.LEFT)
#         self.clock_lbl = tk.Label(ih, font=("Courier", 18, "bold"), bg=CARD, fg="#ffffff"); self.clock_lbl.pack(side=tk.RIGHT)
#         self._tick()

#         body = tk.Frame(self.root, bg=BG, padx=30, pady=20); body.pack(fill=tk.BOTH, expand=True)
        
#         # ID Entry
#         id_f = tk.Frame(body, bg=CARD, highlightbackground="#2a2d3e", highlightthickness=1); id_f.pack(fill=tk.X, pady=10)
#         tk.Label(id_f, text=" WORKER ID", font=("Courier", 8), bg=CARD, fg="#64748b").pack(anchor="w", padx=10, pady=5)
#         self.user_entry = tk.Entry(id_f, font=("Courier", 24, "bold"), width=8, bg="#1e2130", fg="white", bd=0, insertbackground=ACCENT); self.user_entry.pack(side=tk.LEFT, padx=15, pady=10)
#         self.user_entry.bind("<KeyRelease>", lambda e: self._refresh_status())
#         self.user_entry.bind("<Return>", lambda e: self._trigger_enter())
#         self.user_entry.focus_set()
#         self.name_lbl = tk.Label(id_f, text="", font=("Courier", 14), bg=CARD, fg=GREEN); self.name_lbl.pack(side=tk.LEFT, padx=20)

#         # Status
#         self.status_box = tk.Frame(body, bg="#0c1a3a", highlightbackground=ACCENT, highlightthickness=1); self.status_box.pack(fill=tk.X, pady=10)
#         self.status_lbl = tk.Label(self.status_box, text="◉ Ready", font=("Courier", 10), bg="#0c1a3a", fg=ACCENT, pady=10); self.status_lbl.pack()

#         # Buttons
#         btn_f = tk.Frame(body, bg=BG); btn_f.pack(fill=tk.X, pady=10)
#         self.btn_in = tk.Button(btn_f, text="▶ CHECK IN", font=("Courier", 12, "bold"), bg=GREEN, width=15, relief=tk.FLAT, state="disabled", command=lambda: self._trigger("checkin"))
#         self.btn_in.pack(side=tk.LEFT, ipady=8, padx=5)
#         self.btn_out = tk.Button(btn_f, text="◼ CHECK OUT", font=("Courier", 12, "bold"), bg=RED, fg="white", width=15, relief=tk.FLAT, state="disabled", command=lambda: self._trigger("checkout"))
#         self.btn_out.pack(side=tk.LEFT, ipady=8, padx=5)

#         # Log
#         self.log_box = tk.Text(body, font=("Courier", 10), bg=CARD, fg="#e2e8f0", height=12, state="disabled", relief=tk.FLAT, padx=10, pady=10); self.log_box.pack(fill=tk.BOTH, expand=True, pady=10)
#         self.log_box.tag_config("ok", foreground=GREEN); self.log_box.tag_config("err", foreground=RED)

#     def _tick(self):
#         self.clock_lbl.config(text=datetime.now().strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick)

#     def log(self, msg, tag="info"):
#         self.log_box.config(state="normal")
#         self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", tag)
#         self.log_box.see("end"); self.log_box.config(state="disabled")

#     def _refresh_status(self):
#         uid = self.user_entry.get().strip()
#         if not uid: return
#         s = get_worker_status(uid)
#         self.btn_in.config(state="normal" if s=="none" else "disabled")
#         self.btn_out.config(state="normal" if s=="checked_in" else "disabled")
#         color = GREEN if s=="none" else (ORANGE if s=="checked_in" else RED)
#         self.status_box.config(highlightbackground=color); self.status_lbl.config(text=f"STATUS: {s.upper()}", fg=color)

#     def _trigger_enter(self):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy: return
#         s = get_worker_status(uid)
#         if s == "none": self._trigger("checkin")
#         elif s == "checked_in": self._trigger("checkout")

#     def _trigger(self, action):
#         if self._busy: return
#         self._busy = True
#         threading.Thread(target=self._process, args=(self.user_entry.get().strip(), action), daemon=True).start()

#     def _process(self, uid, action):
#         is_open = False
#         try:
#             self.log(f"Starting {action.upper()} for ID {uid}")
#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err"); return
            
#             zk.OpenDevice(0)
#             is_open = True
#             self.root.after(0, lambda: self.status_lbl.config(text="◉ Place finger on sensor...", fg=ORANGE))
            
#             capture = None
#             for _ in range(50):
#                 capture = zk.AcquireFingerprint()
#                 if capture: break
#                 time.sleep(0.2)
            
#             if not capture: self.log("Scan timeout", "err"); return
#             self.log("Scan successful", "ok")

#             worker = find_worker(uid)
#             if not worker: self.log("Worker not in Zoho", "err"); return
#             self.root.after(0, lambda: self.name_lbl.config(text=worker.get("Full_Name", "")))

#             pa = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID
            
#             success, msg = log_attendance(worker["ID"], uid, pid, worker.get("Full_Name"), action)
#             self.log(msg, "ok" if success else "err")

#         except Exception as e:
#             self.log(f"Error: {str(e)}", "err")
#         finally:
#             if is_open:
#                 try: zk.CloseDevice()
#                 except: pass
#             self._busy = False
#             self.root.after(0, lambda: [self.user_entry.delete(0, 'end'), self._refresh_status()])

#     def _on_close(self):
#         try: zk.Terminate()
#         except: pass
#         self.root.destroy()

# if __name__ == "__main__":
#     root = tk.Tk(); app = FingerprintGUI(root); root.mainloop()



# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import font as tkfont

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ===========================================================
# # GLOBAL SDK INITIALIZATION
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     try:
#         return requests.request(method, url, **kwargs)
#     except Exception:
#         return None

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
#     if r and r.status_code == 200:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE MANAGEMENT
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#                 if data.get("date") == today:
#                     return data
#         except:
#             pass
#     return {"date": today, "checked_in": {}, "checked_out": {}}

# def save_lock(data):
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(data, f)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     if str(zk_id) in lock["checked_out"]:
#         return "done"
#     if str(zk_id) in lock["checked_in"]:
#         return "checked_in"
#     return "none"

# # ===========================================================
# # ZOHO API LOGIC
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def log_attendance(worker_id, zk_id, project_id, full_name, action):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         payload = {"data": {
#             "Worker_Name":      worker_id,
#             "Projects":         project_id,
#             "Date":             today_display,
#             "First_In":         checkin_time,
#             "Worker_Full_Name": full_name,
#         }}
#         r = zoho_request("POST", form_url, headers=auth_headers(), json=payload)
#         if r and r.status_code in (200, 201):
#             zoho_rec_id = r.json().get("data", {}).get("ID")
#             lock = load_lock()
#             lock["checked_in"][zk_key] = {"time": checkin_time, "zoho_id": zoho_rec_id}
#             save_lock(lock)
#             return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
#         return False, f"Check-in failed: {r.text if r else 'Timeout'}"

#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "Local check-in record not found."

#         att_record_id = info.get("zoho_id")
#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             crit = f'(Worker_Name == {worker_id} && Date == "{today_iso}")'
#             r_s = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#             if r_s and r_s.status_code == 200 and r_s.json().get("data"):
#                 att_record_id = r_s.json()["data"][0]["ID"]

#         if not att_record_id:
#             return False, "Could not locate the Zoho Record ID for update."

#         try:
#             dt_in = datetime.strptime(info["time"], "%d-%b-%Y %H:%M:%S")
#         except:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)

#         update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}/{att_record_id}"
#         r_u = zoho_request(
#             "PATCH", update_url,
#             headers=auth_headers(),
#             json={"data": {
#                 "Last_Out":    now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Total_Hours": round(total_hours, 4),
#             }}
#         )
#         if r_u and r_u.status_code == 200:
#             res_body = r_u.json()
#             if res_body.get("code") == 3000:
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = now.strftime("%H:%M:%S")
#                 save_lock(lock)
#                 return True, f"🚪  {full_name} checked OUT. Worked: {round(total_hours, 2)} hrs"
#             else:
#                 return False, f"Zoho Error: {res_body.get('message')}"
#         return False, f"Check-out failed (HTTP {r_u.status_code if r_u else 'Timeout'})"

#     return False, "Unknown action"


# # ===========================================================
# # COLOUR PALETTE
# # ===========================================================
# BG          = "#060810"
# CARD        = "#0d1117"
# CARD2       = "#111827"
# BORDER      = "#1e2433"
# ACCENT      = "#3b82f6"
# ACCENT_DIM  = "#1d3a6e"
# GREEN       = "#10b981"
# GREEN_DIM   = "#064e35"
# RED         = "#ef4444"
# RED_DIM     = "#450a0a"
# ORANGE      = "#f59e0b"
# ORANGE_DIM  = "#451a03"
# TEXT        = "#f1f5f9"
# MUTED       = "#475569"
# WHITE       = "#ffffff"
# GOLD        = "#fbbf24"


# # ===========================================================
# # MAIN GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root  = root
#         self.root.title("Real Estate Wages System")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy          = False
#         self._id_check_job  = None   # debounce timer for ID validation
#         self._worker_cache  = {}     # cache validated IDs → worker name

#         # fullscreen-ish fixed size
#         sw = root.winfo_screenwidth()
#         sh = root.winfo_screenheight()
#         W, H = min(sw, 860), min(sh, 720)
#         x = (sw - W) // 2
#         y = (sh - H) // 2
#         self.root.geometry(f"{W}x{H}+{x}+{y}")

#         self._build_ui()
#         self._tick_clock()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD UI ──────────────────────────────────────────
#     def _build_ui(self):
#         # ── HEADER ────────────────────────────────────────
#         hdr = tk.Frame(self.root, bg=CARD, pady=0)
#         hdr.pack(fill=tk.X)

#         # gold accent line at very top
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)

#         hdr_inner = tk.Frame(hdr, bg=CARD, padx=28, pady=16)
#         hdr_inner.pack(fill=tk.X)

#         # LEFT: company name + subtitle
#         left = tk.Frame(hdr_inner, bg=CARD)
#         left.pack(side=tk.LEFT)

#         tk.Label(left, text="REAL ESTATE WAGES SYSTEM",
#                  font=("Courier", 14, "bold"),
#                  bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(left, text="Wavemark Properties Limited  ·  Attendance Terminal",
#                  font=("Courier", 8),
#                  bg=CARD, fg=MUTED).pack(anchor="w", pady=(2, 0))

#         # RIGHT: date + clock stacked
#         right = tk.Frame(hdr_inner, bg=CARD)
#         right.pack(side=tk.RIGHT)

#         self.date_lbl = tk.Label(right, text="",
#                  font=("Courier", 9), bg=CARD, fg=MUTED)
#         self.date_lbl.pack(anchor="e")

#         self.clock_lbl = tk.Label(right, text="",
#                  font=("Courier", 22, "bold"), bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")

#         # ── BODY ──────────────────────────────────────────
#         body = tk.Frame(self.root, bg=BG, padx=32, pady=20)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ── ID INPUT CARD ─────────────────────────────────
#         id_card = tk.Frame(body, bg=CARD2,
#                            highlightbackground=BORDER,
#                            highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 16))

#         id_inner = tk.Frame(id_card, bg=CARD2, padx=20, pady=16)
#         id_inner.pack(fill=tk.X)

#         tk.Label(id_inner, text="WORKER ID",
#                  font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED).pack(anchor="w")

#         entry_row = tk.Frame(id_inner, bg=CARD2)
#         entry_row.pack(fill=tk.X, pady=(6, 0))

#         # Gold-bordered entry
#         eb = tk.Frame(entry_row, bg=GOLD, padx=2, pady=2)
#         eb.pack(side=tk.LEFT)
#         ei = tk.Frame(eb, bg="#0a0e1a")
#         ei.pack()
#         self.user_entry = tk.Entry(
#             ei,
#             font=("Courier", 26, "bold"),
#             width=10, bd=0,
#             bg="#0a0e1a", fg=WHITE,
#             insertbackground=GOLD,
#             selectbackground=GOLD,
#         )
#         self.user_entry.pack(padx=12, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_id_keyrelease)
#         self.user_entry.bind("<Return>",     self._on_enter)
#         self.user_entry.focus_set()

#         # Worker name displayed next to entry
#         name_col = tk.Frame(id_inner, bg=CARD2)
#         name_col.pack(fill=tk.X, pady=(10, 0))

#         self.name_lbl = tk.Label(
#             name_col, text="",
#             font=("Courier", 15, "bold"),
#             bg=CARD2, fg=GREEN)
#         self.name_lbl.pack(anchor="w")

#         self.id_hint_lbl = tk.Label(
#             name_col, text="",
#             font=("Courier", 9),
#             bg=CARD2, fg=MUTED)
#         self.id_hint_lbl.pack(anchor="w")

#         # ── STATUS BANNER ─────────────────────────────────
#         self.status_frame = tk.Frame(body, bg=ACCENT_DIM,
#                                      highlightbackground=ACCENT,
#                                      highlightthickness=1)
#         self.status_frame.pack(fill=tk.X, pady=(0, 16))

#         self.status_lbl = tk.Label(
#             self.status_frame,
#             text="◉   Enter Worker ID to begin",
#             font=("Courier", 10),
#             bg=ACCENT_DIM, fg=ACCENT,
#             pady=11, padx=16, anchor="w")
#         self.status_lbl.pack(fill=tk.X)

#         # ── ACTION BUTTONS ────────────────────────────────
#         btn_row = tk.Frame(body, bg=BG)
#         btn_row.pack(fill=tk.X, pady=(0, 16))

#         self.btn_in = tk.Button(
#             btn_row,
#             text="▶   CHECK  IN",
#             font=("Courier", 12, "bold"),
#             width=18, relief=tk.FLAT,
#             bg=GREEN_DIM, fg=MUTED,
#             activebackground=GREEN, activeforeground=BG,
#             cursor="hand2", state=tk.DISABLED,
#             command=lambda: self._trigger("checkin"),
#         )
#         self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         self.btn_out = tk.Button(
#             btn_row,
#             text="◼   CHECK  OUT",
#             font=("Courier", 12, "bold"),
#             width=18, relief=tk.FLAT,
#             bg=RED_DIM, fg=MUTED,
#             activebackground=RED, activeforeground=WHITE,
#             cursor="hand2", state=tk.DISABLED,
#             command=lambda: self._trigger("checkout"),
#         )
#         self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         # Clear button
#         tk.Button(
#             btn_row, text="✕ CLEAR",
#             font=("Courier", 9, "bold"),
#             relief=tk.FLAT,
#             bg=BORDER, fg=MUTED,
#             activebackground=MUTED, activeforeground=WHITE,
#             cursor="hand2",
#             command=self._reset_ui,
#         ).pack(side=tk.LEFT, ipady=10, padx=(0, 0))

#         # ── DIVIDER ───────────────────────────────────────
#         tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

#         # ── LOG BOX ───────────────────────────────────────
#         log_hdr = tk.Frame(body, bg=BG)
#         log_hdr.pack(fill=tk.X, pady=(0, 6))
#         tk.Label(log_hdr, text="ACTIVITY LOG",
#                  font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         tk.Button(log_hdr, text="CLEAR LOG",
#                   font=("Courier", 7, "bold"),
#                   relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                   activebackground=MUTED, activeforeground=WHITE,
#                   cursor="hand2", padx=6, pady=2,
#                   command=self._clear_log).pack(side=tk.RIGHT)

#         log_wrap = tk.Frame(body, bg=CARD2,
#                             highlightbackground=BORDER,
#                             highlightthickness=1)
#         log_wrap.pack(fill=tk.BOTH, expand=True)

#         sb = tk.Scrollbar(log_wrap, bg=BORDER, troughcolor=CARD2)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)

#         self.log_box = tk.Text(
#             log_wrap,
#             font=("Courier", 10),
#             bg=CARD2, fg=TEXT,
#             relief=tk.FLAT,
#             padx=12, pady=10,
#             yscrollcommand=sb.set,
#             state=tk.DISABLED,
#         )
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#         # colour tags
#         self.log_box.tag_config("ok",   foreground=GREEN)
#         self.log_box.tag_config("err",  foreground=RED)
#         self.log_box.tag_config("warn", foreground=ORANGE)
#         self.log_box.tag_config("info", foreground=ACCENT)
#         self.log_box.tag_config("ts",   foreground=MUTED)
#         self.log_box.tag_config("div",  foreground=BORDER)

#         # ── FLASH OVERLAY (full-screen success/error) ─────
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.flash_icon = tk.Label(self.flash,
#                                    font=("Courier", 60, "bold"),
#                                    bg=ACCENT, fg=WHITE)
#         self.flash_icon.place(relx=0.5, rely=0.38, anchor="center")
#         self.flash_msg  = tk.Label(self.flash,
#                                    font=("Courier", 22, "bold"),
#                                    bg=ACCENT, fg=WHITE,
#                                    wraplength=600)
#         self.flash_msg.place(relx=0.5, rely=0.52, anchor="center")
#         self.flash_sub  = tk.Label(self.flash,
#                                    font=("Courier", 13),
#                                    bg=ACCENT, fg="#c7d9ff",
#                                    wraplength=600)
#         self.flash_sub.place(relx=0.5, rely=0.62, anchor="center")

#     # ── CLOCK ─────────────────────────────────────────────
#     def _tick_clock(self):
#         now = datetime.now()
#         # e.g.  Friday, 21 February 2026
#         self.date_lbl.config(
#             text=now.strftime("%A, %d %B %Y"))
#         # e.g.  09:35:47
#         self.clock_lbl.config(
#             text=now.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── LOG ───────────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             ts = datetime.now().strftime("%H:%M:%S")
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{ts}]  ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _log_div(self):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, "─" * 62 + "\n", "div")
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     # ── FLASH OVERLAY ─────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, color):
#         """Show a full-screen coloured flash for 2 seconds then hide."""
#         self.flash.config(bg=color)
#         self.flash_icon.config(text=icon, bg=color)
#         self.flash_msg.config(text=headline, bg=color)
#         self.flash_sub.config(text=sub, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2000, self.flash.place_forget)

#     # ── STATUS BANNER ─────────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.status_frame.config(bg=bg, highlightbackground=border)
#             self.status_lbl.config(text=text, fg=fg, bg=bg)
#         self.root.after(0, _do)

#     # ── BUTTON STATES ─────────────────────────────────────
#     def _set_buttons(self, in_state, out_state):
#         def _do():
#             if in_state == tk.NORMAL:
#                 self.btn_in.config(state=tk.NORMAL,  bg=GREEN, fg=BG)
#             else:
#                 self.btn_in.config(state=tk.DISABLED, bg=GREEN_DIM, fg=MUTED)
#             if out_state == tk.NORMAL:
#                 self.btn_out.config(state=tk.NORMAL,  bg=RED, fg=WHITE)
#             else:
#                 self.btn_out.config(state=tk.DISABLED, bg=RED_DIM, fg=MUTED)
#         self.root.after(0, _do)

#     def _apply_status(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "◉   Attendance complete for today — see you tomorrow!",
#                 RED, RED_DIM, RED)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status(
#                 "◉   Already CHECKED IN — proceed to Check-Out",
#                 ORANGE, ORANGE_DIM, ORANGE)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status(
#                 "◉   Ready to CHECK IN",
#                 GREEN, GREEN_DIM, GREEN)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "◉   Enter Worker ID to begin",
#                 ACCENT, ACCENT_DIM, ACCENT)

#     # ── ID KEYRELEASE — debounced validation ──────────────
#     def _on_id_keyrelease(self, _event=None):
#         # Cancel previous pending check
#         if self._id_check_job:
#             self.root.after_cancel(self._id_check_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._reset_ui_soft()
#             return
#         # Show local status immediately (fast, no network)
#         status = get_worker_status(uid)
#         self._apply_status(status)
#         # Debounce: after 600ms of no typing, validate against Zoho
#         self._id_check_job = self.root.after(600, lambda: self._validate_id(uid))

#     def _validate_id(self, uid):
#         """Background thread: check if the ID exists in Zoho."""
#         if not uid or self._busy:
#             return
#         # Only validate if still the same ID
#         if self.user_entry.get().strip() != uid:
#             return
#         threading.Thread(target=self._do_validate, args=(uid,), daemon=True).start()

#     def _do_validate(self, uid):
#         # Check cache first
#         if uid in self._worker_cache:
#             worker = self._worker_cache[uid]
#         else:
#             worker = find_worker(uid)
#             if worker:
#                 self._worker_cache[uid] = worker

#         if self.user_entry.get().strip() != uid:
#             return  # user typed something else while we were fetching

#         def _update():
#             if not worker:
#                 # ID does not exist in Zoho
#                 self.name_lbl.config(text="", fg=RED)
#                 self.id_hint_lbl.config(
#                     text=f"✗  ID {uid!r} not found in system — contact admin",
#                     fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(
#                     f"◉   Worker ID {uid} does not exist",
#                     RED, RED_DIM, RED)
#             else:
#                 full_name = worker.get("Full_Name", "N/A")
#                 status    = get_worker_status(uid)
#                 self.name_lbl.config(text=full_name, fg=GREEN)
#                 # Contextual hint
#                 if status == "checked_in":
#                     self.id_hint_lbl.config(
#                         text="Already checked IN today — use Check-Out ↓",
#                         fg=ORANGE)
#                 elif status == "done":
#                     self.id_hint_lbl.config(
#                         text="Attendance complete for today",
#                         fg=RED)
#                 else:
#                     self.id_hint_lbl.config(
#                         text="Ready to check in",
#                         fg=MUTED)
#                 self._apply_status(status)
#         self.root.after(0, _update)

#     def _on_enter(self, _event=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy:
#             return
#         status = get_worker_status(uid)
#         if status == "none":
#             self._trigger("checkin")
#         elif status == "checked_in":
#             self._trigger("checkout")

#     # ── TRIGGER ───────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉   Scanning fingerprint...", ORANGE, ORANGE_DIM, ORANGE)
#         threading.Thread(
#             target=self._process, args=(uid, action), daemon=True
#         ).start()

#     # ── BACKGROUND PROCESS ────────────────────────────────
#     def _process(self, uid, action):
#         is_open = False
#         try:
#             self._log_div()
#             self.log(f"Starting {action.upper()} for ID {uid}", "info")

#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Please connect the fingerprint device and try again.",
#                     "#7c3aed"))
#                 return

#             zk.OpenDevice(0)
#             is_open = True
#             self.log("Place your finger on the scanner...", "info")

#             capture = None
#             for _ in range(150):   # 30 seconds
#                 capture = zk.AcquireFingerprint()
#                 if capture:
#                     break
#                 time.sleep(0.2)

#             if not capture:
#                 self.log("Fingerprint scan timed out", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout",
#                     "No fingerprint detected. Please try again.",
#                     "#b45309"))
#                 return

#             self.log("Fingerprint captured", "ok")

#             # Look up worker
#             if uid in self._worker_cache:
#                 worker = self._worker_cache[uid]
#             else:
#                 worker = find_worker(uid)
#                 if worker:
#                     self._worker_cache[uid] = worker

#             if not worker:
#                 self.log(f"Worker ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found",
#                     f"ID {uid} does not exist in the system.",
#                     RED))
#                 return

#             full_name = worker.get("Full_Name", "N/A")
#             self.log(f"Worker: {full_name}", "ok")

#             # Re-check status
#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log(f"{full_name} — attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Done",
#                     f"{full_name}",
#                     "#7c3aed"))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log(f"{full_name} already checked IN — redirecting to Check-Out", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In",
#                     f"{full_name} — please use Check-Out",
#                     ORANGE_DIM if False else "#92400e"))
#                 self.root.after(2100, lambda: self._apply_status("checked_in"))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log(f"{full_name} has not checked IN yet", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In",
#                     f"{full_name} — please Check In first",
#                     "#7c3aed"))
#                 return

#             # Resolve project
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID

#             # Post to Zoho
#             self.log(f"Posting {action.upper()} to Zoho...", "info")
#             success, msg = log_attendance(
#                 worker["ID"], uid, pid, full_name, action
#             )
#             self.log(msg, "ok" if success else "err")

#             if success:
#                 if action == "checkin":
#                     self.root.after(0, lambda: self._show_flash(
#                         "✔",
#                         f"Checked IN  —  {full_name}",
#                         datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y"),
#                         "#1d4ed8"))
#                 else:
#                     self.root.after(0, lambda: self._show_flash(
#                         "✔",
#                         f"Checked OUT  —  {full_name}",
#                         datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y"),
#                         "#1d4ed8"))
#             else:
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", msg[:80], RED))

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")

#         finally:
#             if is_open:
#                 try:
#                     zk.CloseDevice()
#                 except:
#                     pass
#             self._busy = False
#             # After flash disappears (2s) reset the whole UI for next user
#             self.root.after(2200, self._reset_ui)

#     # ── RESET UI — clears everything for the next user ────
#     def _reset_ui(self):
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="")
#         self.id_hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status(
#             "◉   Enter Worker ID to begin",
#             ACCENT, ACCENT_DIM, ACCENT)
#         self.user_entry.focus_set()
#         self._log_div()
#         self.log("Ready for next worker.", "info")

#     def _reset_ui_soft(self):
#         """Reset without touching the log — for empty-field keyrelease."""
#         self.name_lbl.config(text="")
#         self.id_hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status(
#             "◉   Enter Worker ID to begin",
#             ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ─────────────────────────────────────────────
#     def _on_close(self):
#         try:
#             zk.Terminate()
#         except:
#             pass
#         self.root.destroy()


# # ===========================================================
# # ENTRY POINT
# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     app  = FingerprintGUI(root)
#     root.mainloop()



# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import font as tkfont

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ===========================================================
# # GLOBAL SDK INITIALIZATION
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     try:
#         return requests.request(method, url, **kwargs)
#     except Exception:
#         return None

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
#     if r and r.status_code == 200:
#         result = r.json()
#         TOKEN_CACHE["token"]      = result.get("access_token")
#         TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#         return TOKEN_CACHE["token"]
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE MANAGEMENT
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#                 if data.get("date") == today:
#                     return data
#         except:
#             pass
#     return {"date": today, "checked_in": {}, "checked_out": {}}

# def save_lock(data):
#     with open(CHECKIN_LOCK_FILE, "w") as f:
#         json.dump(data, f)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     if str(zk_id) in lock["checked_out"]:
#         return "done"
#     if str(zk_id) in lock["checked_in"]:
#         return "checked_in"
#     return "none"

# # ===========================================================
# # ZOHO API LOGIC
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def log_attendance(worker_id, zk_id, project_id, full_name, action):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         payload = {"data": {
#             "Worker_Name":      worker_id,
#             "Projects":         project_id,
#             "Date":             today_display,
#             "First_In":         checkin_time,
#             "Worker_Full_Name": full_name,
#         }}
#         r = zoho_request("POST", form_url, headers=auth_headers(), json=payload)
#         if r and r.status_code in (200, 201):
#             zoho_rec_id = r.json().get("data", {}).get("ID")
#             lock = load_lock()
#             lock["checked_in"][zk_key] = {"time": checkin_time, "zoho_id": zoho_rec_id}
#             save_lock(lock)
#             return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
#         return False, f"Check-in failed: {r.text if r else 'Timeout'}"

#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "Local check-in record not found."

#         att_record_id = info.get("zoho_id")
#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             crit = f'(Worker_Name == {worker_id} && Date == "{today_iso}")'
#             r_s = zoho_request("GET", report_url, headers=auth_headers(), params={"criteria": crit})
#             if r_s and r_s.status_code == 200 and r_s.json().get("data"):
#                 att_record_id = r_s.json()["data"][0]["ID"]

#         if not att_record_id:
#             return False, "Could not locate the Zoho Record ID for update."

#         try:
#             dt_in = datetime.strptime(info["time"], "%d-%b-%Y %H:%M:%S")
#         except:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)

#         update_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}/{att_record_id}"
#         r_u = zoho_request(
#             "PATCH", update_url,
#             headers=auth_headers(),
#             json={"data": {
#                 "Last_Out":    now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Total_Hours": round(total_hours, 4),
#             }}
#         )
#         if r_u and r_u.status_code == 200:
#             res_body = r_u.json()
#             if res_body.get("code") == 3000:
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = now.strftime("%H:%M:%S")
#                 save_lock(lock)
#                 return True, f"🚪  {full_name} checked OUT. Worked: {round(total_hours, 2)} hrs"
#             else:
#                 return False, f"Zoho Error: {res_body.get('message')}"
#         return False, f"Check-out failed (HTTP {r_u.status_code if r_u else 'Timeout'})"

#     return False, "Unknown action"


# # ===========================================================
# # COLOUR PALETTE
# # ===========================================================
# BG          = "#060810"
# CARD        = "#0d1117"
# CARD2       = "#111827"
# BORDER      = "#1e2433"
# ACCENT      = "#3b82f6"
# ACCENT_DIM  = "#1d3a6e"
# GREEN       = "#10b981"
# GREEN_DIM   = "#064e35"
# RED         = "#ef4444"
# RED_DIM     = "#450a0a"
# ORANGE      = "#f59e0b"
# ORANGE_DIM  = "#451a03"
# TEXT        = "#f1f5f9"
# MUTED       = "#475569"
# WHITE       = "#ffffff"
# GOLD        = "#fbbf24"


# # ===========================================================
# # MAIN GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root  = root
#         self.root.title("Real Estate Wages System")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy          = False
#         self._id_check_job  = None   # debounce timer for ID validation
#         self._worker_cache  = {}     # cache validated IDs → worker name

#         # fullscreen-ish fixed size
#         sw = root.winfo_screenwidth()
#         sh = root.winfo_screenheight()
#         W, H = min(sw, 860), min(sh, 720)
#         x = (sw - W) // 2
#         y = (sh - H) // 2
#         self.root.geometry(f"{W}x{H}+{x}+{y}")

#         self._build_ui()
#         self._tick_clock()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD UI ──────────────────────────────────────────
#     def _build_ui(self):
#         # ── HEADER ────────────────────────────────────────
#         hdr = tk.Frame(self.root, bg=CARD, pady=0)
#         hdr.pack(fill=tk.X)

#         # gold accent line at very top
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)

#         hdr_inner = tk.Frame(hdr, bg=CARD, padx=28, pady=16)
#         hdr_inner.pack(fill=tk.X)

#         # LEFT: company name + subtitle
#         left = tk.Frame(hdr_inner, bg=CARD)
#         left.pack(side=tk.LEFT)

#         tk.Label(left, text="REAL ESTATE WAGES SYSTEM",
#                  font=("Courier", 14, "bold"),
#                  bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(left, text="Wavemark Properties Limited  ·  Attendance Terminal",
#                  font=("Courier", 8),
#                  bg=CARD, fg=MUTED).pack(anchor="w", pady=(2, 0))

#         # RIGHT: date + clock stacked
#         right = tk.Frame(hdr_inner, bg=CARD)
#         right.pack(side=tk.RIGHT)

#         self.date_lbl = tk.Label(right, text="",
#                  font=("Courier", 9), bg=CARD, fg=MUTED)
#         self.date_lbl.pack(anchor="e")

#         self.clock_lbl = tk.Label(right, text="",
#                  font=("Courier", 22, "bold"), bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")

#         # ── BODY ──────────────────────────────────────────
#         body = tk.Frame(self.root, bg=BG, padx=32, pady=20)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ── ID INPUT CARD ─────────────────────────────────
#         id_card = tk.Frame(body, bg=CARD2,
#                            highlightbackground=BORDER,
#                            highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 16))

#         id_inner = tk.Frame(id_card, bg=CARD2, padx=20, pady=16)
#         id_inner.pack(fill=tk.X)

#         tk.Label(id_inner, text="WORKER ID",
#                  font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED).pack(anchor="w")

#         entry_row = tk.Frame(id_inner, bg=CARD2)
#         entry_row.pack(fill=tk.X, pady=(6, 0))

#         # Gold-bordered entry
#         eb = tk.Frame(entry_row, bg=GOLD, padx=2, pady=2)
#         eb.pack(side=tk.LEFT)
#         ei = tk.Frame(eb, bg="#0a0e1a")
#         ei.pack()
#         self.user_entry = tk.Entry(
#             ei,
#             font=("Courier", 26, "bold"),
#             width=10, bd=0,
#             bg="#0a0e1a", fg=WHITE,
#             insertbackground=GOLD,
#             selectbackground=GOLD,
#         )
#         self.user_entry.pack(padx=12, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_id_keyrelease)
#         self.user_entry.bind("<Return>",     self._on_enter)
#         self.user_entry.focus_set()

#         # Worker name displayed next to entry
#         name_col = tk.Frame(id_inner, bg=CARD2)
#         name_col.pack(fill=tk.X, pady=(10, 0))

#         self.name_lbl = tk.Label(
#             name_col, text="",
#             font=("Courier", 15, "bold"),
#             bg=CARD2, fg=GREEN)
#         self.name_lbl.pack(anchor="w")

#         self.id_hint_lbl = tk.Label(
#             name_col, text="",
#             font=("Courier", 9),
#             bg=CARD2, fg=MUTED)
#         self.id_hint_lbl.pack(anchor="w")

#         # ── STATUS BANNER ─────────────────────────────────
#         self.status_frame = tk.Frame(body, bg=ACCENT_DIM,
#                                      highlightbackground=ACCENT,
#                                      highlightthickness=1)
#         self.status_frame.pack(fill=tk.X, pady=(0, 16))

#         self.status_lbl = tk.Label(
#             self.status_frame,
#             text="◉   Enter Worker ID to begin",
#             font=("Courier", 10),
#             bg=ACCENT_DIM, fg=ACCENT,
#             pady=11, padx=16, anchor="w")
#         self.status_lbl.pack(fill=tk.X)

#         # ── ACTION BUTTONS ────────────────────────────────
#         btn_row = tk.Frame(body, bg=BG)
#         btn_row.pack(fill=tk.X, pady=(0, 16))

#         self.btn_in = tk.Button(
#             btn_row,
#             text="▶   CHECK  IN",
#             font=("Courier", 12, "bold"),
#             width=18, relief=tk.FLAT,
#             bg=GREEN_DIM, fg=MUTED,
#             activebackground=GREEN, activeforeground=BG,
#             cursor="hand2", state=tk.DISABLED,
#             command=lambda: self._trigger("checkin"),
#         )
#         self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         self.btn_out = tk.Button(
#             btn_row,
#             text="◼   CHECK  OUT",
#             font=("Courier", 12, "bold"),
#             width=18, relief=tk.FLAT,
#             bg=RED_DIM, fg=MUTED,
#             activebackground=RED, activeforeground=WHITE,
#             cursor="hand2", state=tk.DISABLED,
#             command=lambda: self._trigger("checkout"),
#         )
#         self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         # Clear button
#         tk.Button(
#             btn_row, text="✕ CLEAR",
#             font=("Courier", 9, "bold"),
#             relief=tk.FLAT,
#             bg=BORDER, fg=MUTED,
#             activebackground=MUTED, activeforeground=WHITE,
#             cursor="hand2",
#             command=self._reset_ui,
#         ).pack(side=tk.LEFT, ipady=10, padx=(0, 0))

#         # ── DIVIDER ───────────────────────────────────────
#         tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

#         # ── LOG BOX ───────────────────────────────────────
#         log_hdr = tk.Frame(body, bg=BG)
#         log_hdr.pack(fill=tk.X, pady=(0, 6))
#         tk.Label(log_hdr, text="ACTIVITY LOG",
#                  font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         tk.Button(log_hdr, text="CLEAR LOG",
#                   font=("Courier", 7, "bold"),
#                   relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                   activebackground=MUTED, activeforeground=WHITE,
#                   cursor="hand2", padx=6, pady=2,
#                   command=self._clear_log).pack(side=tk.RIGHT)

#         log_wrap = tk.Frame(body, bg=CARD2,
#                             highlightbackground=BORDER,
#                             highlightthickness=1)
#         log_wrap.pack(fill=tk.BOTH, expand=True)

#         sb = tk.Scrollbar(log_wrap, bg=BORDER, troughcolor=CARD2)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)

#         self.log_box = tk.Text(
#             log_wrap,
#             font=("Courier", 10),
#             bg=CARD2, fg=TEXT,
#             relief=tk.FLAT,
#             padx=12, pady=10,
#             yscrollcommand=sb.set,
#             state=tk.DISABLED,
#         )
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#         # colour tags
#         self.log_box.tag_config("ok",   foreground=GREEN)
#         self.log_box.tag_config("err",  foreground=RED)
#         self.log_box.tag_config("warn", foreground=ORANGE)
#         self.log_box.tag_config("info", foreground=ACCENT)
#         self.log_box.tag_config("ts",   foreground=MUTED)
#         self.log_box.tag_config("div",  foreground=BORDER)

#         # ── FLASH OVERLAY (full-screen success/error) ─────
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.flash_icon = tk.Label(self.flash,
#                                    font=("Courier", 60, "bold"),
#                                    bg=ACCENT, fg=WHITE)
#         self.flash_icon.place(relx=0.5, rely=0.38, anchor="center")
#         self.flash_msg  = tk.Label(self.flash,
#                                    font=("Courier", 22, "bold"),
#                                    bg=ACCENT, fg=WHITE,
#                                    wraplength=600)
#         self.flash_msg.place(relx=0.5, rely=0.52, anchor="center")
#         self.flash_sub  = tk.Label(self.flash,
#                                    font=("Courier", 13),
#                                    bg=ACCENT, fg="#c7d9ff",
#                                    wraplength=600)
#         self.flash_sub.place(relx=0.5, rely=0.62, anchor="center")

#     # ── CLOCK ─────────────────────────────────────────────
#     def _tick_clock(self):
#         now = datetime.now()
#         # e.g.  Friday, 21 February 2026
#         self.date_lbl.config(
#             text=now.strftime("%A, %d %B %Y"))
#         # e.g.  09:35:47
#         self.clock_lbl.config(
#             text=now.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── LOG ───────────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             ts = datetime.now().strftime("%H:%M:%S")
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{ts}]  ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _log_div(self):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, "─" * 62 + "\n", "div")
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     # ── FLASH OVERLAY ─────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, color):
#         """Show a full-screen coloured flash for 2 seconds then hide."""
#         self.flash.config(bg=color)
#         self.flash_icon.config(text=icon, bg=color)
#         self.flash_msg.config(text=headline, bg=color)
#         self.flash_sub.config(text=sub, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2000, self.flash.place_forget)

#     # ── STATUS BANNER ─────────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.status_frame.config(bg=bg, highlightbackground=border)
#             self.status_lbl.config(text=text, fg=fg, bg=bg)
#         self.root.after(0, _do)

#     # ── BUTTON STATES ─────────────────────────────────────
#     def _set_buttons(self, in_state, out_state):
#         def _do():
#             if in_state == tk.NORMAL:
#                 self.btn_in.config(state=tk.NORMAL,  bg=GREEN, fg=BG)
#             else:
#                 self.btn_in.config(state=tk.DISABLED, bg=GREEN_DIM, fg=MUTED)
#             if out_state == tk.NORMAL:
#                 self.btn_out.config(state=tk.NORMAL,  bg=RED, fg=WHITE)
#             else:
#                 self.btn_out.config(state=tk.DISABLED, bg=RED_DIM, fg=MUTED)
#         self.root.after(0, _do)

#     def _apply_status(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "◉   Attendance complete for today — see you tomorrow!",
#                 RED, RED_DIM, RED)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status(
#                 "◉   Already CHECKED IN — proceed to Check-Out",
#                 ORANGE, ORANGE_DIM, ORANGE)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status(
#                 "◉   Ready to CHECK IN",
#                 GREEN, GREEN_DIM, GREEN)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status(
#                 "◉   Enter Worker ID to begin",
#                 ACCENT, ACCENT_DIM, ACCENT)

#     # ── ID KEYRELEASE — debounced validation ──────────────
#     def _on_id_keyrelease(self, _event=None):
#         # Cancel previous pending check
#         if self._id_check_job:
#             self.root.after_cancel(self._id_check_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._reset_ui_soft()
#             return
#         # Show local status immediately (fast, no network)
#         status = get_worker_status(uid)
#         self._apply_status(status)
#         # Debounce: after 600ms of no typing, validate against Zoho
#         self._id_check_job = self.root.after(600, lambda: self._validate_id(uid))

#     def _validate_id(self, uid):
#         """Background thread: check if the ID exists in Zoho."""
#         if not uid or self._busy:
#             return
#         # Only validate if still the same ID
#         if self.user_entry.get().strip() != uid:
#             return
#         threading.Thread(target=self._do_validate, args=(uid,), daemon=True).start()

#     def _do_validate(self, uid):
#         # Check cache first
#         if uid in self._worker_cache:
#             worker = self._worker_cache[uid]
#         else:
#             worker = find_worker(uid)
#             if worker:
#                 self._worker_cache[uid] = worker

#         if self.user_entry.get().strip() != uid:
#             return  # user typed something else while we were fetching

#         def _update():
#             if not worker:
#                 # ID does not exist in Zoho
#                 self.name_lbl.config(text="", fg=RED)
#                 self.id_hint_lbl.config(
#                     text=f"✗  ID {uid!r} not found in system — contact admin",
#                     fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(
#                     f"◉   Worker ID {uid} does not exist",
#                     RED, RED_DIM, RED)
#             else:
#                 full_name = worker.get("Full_Name", "N/A")
#                 status    = get_worker_status(uid)
#                 self.name_lbl.config(text=full_name, fg=GREEN)
#                 # Contextual hint
#                 if status == "checked_in":
#                     self.id_hint_lbl.config(
#                         text="Already checked IN today — use Check-Out ↓",
#                         fg=ORANGE)
#                 elif status == "done":
#                     self.id_hint_lbl.config(
#                         text="Attendance complete for today",
#                         fg=RED)
#                 else:
#                     self.id_hint_lbl.config(
#                         text="Ready to check in",
#                         fg=MUTED)
#                 self._apply_status(status)
#         self.root.after(0, _update)

#     def _on_enter(self, _event=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy:
#             return
#         status = get_worker_status(uid)
#         if status == "none":
#             self._trigger("checkin")
#         elif status == "checked_in":
#             self._trigger("checkout")

#     # ── TRIGGER ───────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy:
#             return
#         uid = self.user_entry.get().strip()
#         if not uid:
#             return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉   Scanning fingerprint...", ORANGE, ORANGE_DIM, ORANGE)
#         threading.Thread(
#             target=self._process, args=(uid, action), daemon=True
#         ).start()

#     # ── BACKGROUND PROCESS ────────────────────────────────
#     def _process(self, uid, action):
#         is_open = False
#         try:
#             self._log_div()
#             self.log(f"Starting {action.upper()} for ID {uid}", "info")

#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Please connect the fingerprint device and try again.",
#                     "#7c3aed"))
#                 return

#             zk.OpenDevice(0)
#             is_open = True
#             self.log("Place your finger on the scanner...", "info")

#             capture = None
#             for _ in range(150):   # 30 seconds
#                 capture = zk.AcquireFingerprint()
#                 if capture:
#                     break
#                 time.sleep(0.2)

#             if not capture:
#                 self.log("Fingerprint scan timed out", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout",
#                     "No fingerprint detected. Please try again.",
#                     "#b45309"))
#                 return

#             self.log("Fingerprint captured", "ok")

#             # Look up worker
#             if uid in self._worker_cache:
#                 worker = self._worker_cache[uid]
#             else:
#                 worker = find_worker(uid)
#                 if worker:
#                     self._worker_cache[uid] = worker

#             if not worker:
#                 self.log(f"Worker ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found",
#                     f"ID {uid} does not exist in the system.",
#                     RED))
#                 return

#             full_name = worker.get("Full_Name", "N/A")
#             self.log(f"Worker: {full_name}", "ok")

#             # Re-check status
#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log(f"{full_name} — attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Done",
#                     f"{full_name}",
#                     "#7c3aed"))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log(f"{full_name} already checked IN — redirecting to Check-Out", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In",
#                     f"{full_name} — please use Check-Out",
#                     ORANGE_DIM if False else "#92400e"))
#                 self.root.after(2100, lambda: self._apply_status("checked_in"))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log(f"{full_name} has not checked IN yet", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In",
#                     f"{full_name} — please Check In first",
#                     "#7c3aed"))
#                 return

#             # Resolve project
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID

#             # Post to Zoho
#             self.log(f"Posting {action.upper()} to Zoho...", "info")
#             success, msg = log_attendance(
#                 worker["ID"], uid, pid, full_name, action
#             )
#             self.log(msg, "ok" if success else "err")

#             if success:
#                 if action == "checkin":
#                     self.root.after(0, lambda: self._show_flash(
#                         "✔",
#                         f"Checked IN  —  {full_name}",
#                         datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y"),
#                         "#1d4ed8"))
#                 else:
#                     self.root.after(0, lambda: self._show_flash(
#                         "✔",
#                         f"Checked OUT  —  {full_name}",
#                         datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y"),
#                         "#1d4ed8"))
#             else:
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", msg[:80], RED))

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")

#         finally:
#             if is_open:
#                 try:
#                     zk.CloseDevice()
#                 except:
#                     pass
#             self._busy = False
#             # After flash disappears (2s) reset entire UI + clear log for next worker
#             self.root.after(2200, lambda: self._reset_ui(clear_log=True))

#     # ── RESET UI — clears EVERYTHING for the next user ──────
#     def _reset_ui(self, clear_log=False):
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="")
#         self.id_hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status(
#             "◉   Enter Worker ID to begin",
#             ACCENT, ACCENT_DIM, ACCENT)
#         self.user_entry.focus_set()
#         if clear_log:
#             # Wipe the log completely — fresh start for next worker
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.delete("1.0", tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.log("─" * 30 + "  Ready for next worker  " + "─" * 30, "div")

#     def _reset_ui_soft(self):
#         """Reset without touching the log — for empty-field keyrelease."""
#         self.name_lbl.config(text="")
#         self.id_hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status(
#             "◉   Enter Worker ID to begin",
#             ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ─────────────────────────────────────────────
#     def _on_close(self):
#         try:
#             zk.Terminate()
#         except:
#             pass
#         self.root.destroy()


# # ===========================================================
# # ENTRY POINT
# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     app  = FingerprintGUI(root)
#     root.mainloop()



# import os, time, json, requests, threading
# from datetime import datetime
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ===========================================================
# # GLOBAL SDK
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, retries=3, **kwargs):
#     """Retry wrapper — keeps trying on network errors all day long."""
#     kwargs.setdefault("timeout", 45)
#     last_exc = None
#     for attempt in range(1, retries + 1):
#         try:
#             r = requests.request(method, url, **kwargs)
#             return r
#         except (requests.exceptions.Timeout,
#                 requests.exceptions.ConnectionError, OSError) as e:
#             last_exc = e
#             if attempt < retries:
#                 time.sleep(2 * attempt)
#     return None

# def get_access_token():
#     """Always return a valid token — refreshes automatically throughout the day."""
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
#         return TOKEN_CACHE["token"]
#     # Token expired or about to — refresh it
#     TOKEN_CACHE["token"] = None   # clear so we never use a stale token
#     url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {
#         "refresh_token": REFRESH_TOKEN,
#         "client_id":     CLIENT_ID,
#         "client_secret": CLIENT_SECRET,
#         "grant_type":    "refresh_token",
#     }
#     # Try up to 3 times in case of transient network error
#     for _ in range(3):
#         r = zoho_request("POST", url, data=data, retries=1)
#         if r and r.status_code == 200:
#             result = r.json()
#             TOKEN_CACHE["token"]      = result.get("access_token")
#             TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
#             return TOKEN_CACHE["token"]
#         time.sleep(3)
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE — persists across the ENTIRE day
# # ===========================================================
# def load_lock():
#     """
#     Load today's attendance state from disk.
#     File is keyed by date so it naturally resets at midnight —
#     workers who check in at 7 AM can still check out at 6 PM.
#     """
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#             if data.get("date") == today:
#                 return data   # same day — return as-is (survives app restarts)
#         except Exception:
#             pass
#     # New day or corrupt file — start fresh
#     fresh = {"date": today, "checked_in": {}, "checked_out": {}}
#     save_lock(fresh)
#     return fresh

# def save_lock(data):
#     """Write state atomically so a crash never corrupts the file."""
#     tmp = CHECKIN_LOCK_FILE + ".tmp"
#     with open(tmp, "w") as f:
#         json.dump(data, f, indent=2)
#     os.replace(tmp, CHECKIN_LOCK_FILE)   # atomic on all major OS

# def get_worker_status(zk_id):
#     lock = load_lock()
#     key  = str(zk_id)
#     if key in lock["checked_out"]:  return "done"
#     if key in lock["checked_in"]:   return "checked_in"
#     return "none"

# def get_checkin_info(zk_id):
#     """Return the stored {time, zoho_id} dict for this worker, or None."""
#     return load_lock()["checked_in"].get(str(zk_id))

# # ===========================================================
# # ZOHO API
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs):
#     """
#     Fallback: search Zoho for today's attendance record when the
#     local zoho_id is missing (e.g. after an app restart mid-day).
#     Tries multiple criteria so it always finds the right record.
#     """
#     report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     for crit in [
#         f'(Worker_Name == {worker_id} && Date == "{today_display}")',
#         f'(Worker_Name == {worker_id} && Date == "{today_iso}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
#         f'(Worker_Name == {worker_id})',
#     ]:
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if r and r.status_code == 200:
#             recs = r.json().get("data", [])
#             if recs:
#                 # If multiple, pick the one matching today
#                 for rec in recs:
#                     d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
#                     if d in (today_display, today_iso):
#                         return rec["ID"]
#                 # Fall back to the first record if date-match failed
#                 return recs[0]["ID"]
#     return None

# def log_attendance(worker_id, zk_id, project_id, full_name, action):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     # ── CHECK-IN ──────────────────────────────────────────
#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         hdrs = auth_headers()

#         payload = {"data": {
#             "Worker_Name":      worker_id,
#             "Projects":         project_id,
#             "Date":             today_display,
#             "First_In":         checkin_time,
#             "Worker_Full_Name": full_name,
#         }}

#         r = zoho_request("POST", form_url, headers=hdrs, json=payload)
#         if r and r.status_code in (200, 201):
#             res  = r.json()
#             # Extract Zoho record ID from every known response structure
#             zoho_rec_id = (
#                 res.get("data", {}).get("ID")
#                 or res.get("ID")
#                 or (res.get("data", [{}])[0].get("ID")
#                     if isinstance(res.get("data"), list) else None)
#             )
#             lock = load_lock()
#             lock["checked_in"][zk_key] = {
#                 "time":    checkin_time,
#                 "zoho_id": zoho_rec_id,
#             }
#             save_lock(lock)
#             return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
#         err = r.text[:200] if r else "Timeout"
#         return False, f"Check-in failed: {err}"

#     # ── CHECK-OUT ─────────────────────────────────────────
#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "No check-in record found for today."

#         hdrs = auth_headers()
#         if not hdrs:
#             return False, "Could not refresh Zoho token — check internet connection."

#         att_record_id = info.get("zoho_id")

#         # ── If zoho_id missing (app restarted), search Zoho ───────────
#         if not att_record_id:
#             att_record_id = _find_record_in_zoho(
#                 worker_id, today_display, today_iso, hdrs)

#         if not att_record_id:
#             return False, (
#                 f"Could not locate today's attendance record in Zoho.\n"
#                 f"Worker: {full_name}  Date: {today_display}\n"
#                 "Please check Daily_Attendance_Report manually."
#             )

#         # ── Calculate hours ────────────────────────────────────────────
#         checkin_time_str = info.get("time", "")
#         try:
#             dt_in = datetime.strptime(checkin_time_str, "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)
#         total_str   = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

#         # ── PATCH the record ───────────────────────────────────────────
#         update_url = (
#             f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#             f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
#         )
#         r_u = zoho_request(
#             "PATCH", update_url,
#             headers=hdrs,
#             json={"data": {
#                 "Last_Out":    now.strftime("%d-%b-%Y %H:%M:%S"),
#                 "Total_Hours": round(total_hours, 4),
#             }},
#         )

#         if r_u and r_u.status_code == 200:
#             body = r_u.json()
#             code = body.get("code")
#             if code == 3000:
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = now.strftime("%H:%M:%S")
#                 save_lock(lock)
#                 return True, (
#                     f"🚪  {full_name} checked OUT at {now.strftime('%H:%M')}\n"
#                     f"    Total time worked: {total_str}"
#                 )
#             # Zoho returned 200 but with a non-success code
#             return False, f"Zoho error (code {code}): {body.get('message', '')}"

#         http = r_u.status_code if r_u else "timeout"
#         body = r_u.text[:200] if r_u else "No response"
#         return False, f"Check-out failed (HTTP {http}): {body}"

#     return False, "Unknown action."


# # ===========================================================
# # COLOUR PALETTE
# # ===========================================================
# BG         = "#060810"
# CARD       = "#0d1117"
# CARD2      = "#111827"
# BORDER     = "#1e2433"
# ACCENT     = "#3b82f6"
# ACCENT_DIM = "#1d3a6e"
# GREEN      = "#10b981"
# GREEN_DIM  = "#064e35"
# RED        = "#ef4444"
# RED_DIM    = "#450a0a"
# ORANGE     = "#f59e0b"
# ORANGE_DIM = "#451a03"
# TEXT       = "#f1f5f9"
# MUTED      = "#475569"
# WHITE      = "#ffffff"
# GOLD       = "#fbbf24"


# # ===========================================================
# # GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root         = root
#         self.root.title("Real Estate Wages System")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy         = False
#         self._debounce_job = None
#         self._worker_cache = {}   # uid → worker dict (lives for the session)

#         sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
#         W, H   = min(sw, 860), min(sh, 720)
#         self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

#         self._build_ui()
#         self._tick_clock()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD ─────────────────────────────────────────────
#     def _build_ui(self):
#         # HEADER
#         hdr = tk.Frame(self.root, bg=CARD)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)

#         hi = tk.Frame(hdr, bg=CARD, padx=28, pady=16)
#         hi.pack(fill=tk.X)

#         lf = tk.Frame(hi, bg=CARD)
#         lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="REAL ESTATE WAGES SYSTEM",
#                  font=("Courier", 14, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(lf, text="Wavemark Properties Limited  ·  Attendance Terminal",
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2,0))

#         rf = tk.Frame(hi, bg=CARD)
#         rf.pack(side=tk.RIGHT)
#         self.date_lbl  = tk.Label(rf, text="", font=("Courier", 9),
#                                    bg=CARD, fg=MUTED)
#         self.date_lbl.pack(anchor="e")
#         self.clock_lbl = tk.Label(rf, text="", font=("Courier", 22, "bold"),
#                                    bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")

#         # BODY
#         body = tk.Frame(self.root, bg=BG, padx=32, pady=20)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ID CARD
#         id_card = tk.Frame(body, bg=CARD2,
#                            highlightbackground=BORDER, highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 16))
#         id_i = tk.Frame(id_card, bg=CARD2, padx=20, pady=16)
#         id_i.pack(fill=tk.X)

#         tk.Label(id_i, text="WORKER ID", font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED).pack(anchor="w")

#         er = tk.Frame(id_i, bg=CARD2)
#         er.pack(fill=tk.X, pady=(6, 0))

#         eb = tk.Frame(er, bg=GOLD, padx=2, pady=2)
#         eb.pack(side=tk.LEFT)
#         ei = tk.Frame(eb, bg="#0a0e1a")
#         ei.pack()
#         self.user_entry = tk.Entry(ei, font=("Courier", 26, "bold"),
#                                    width=10, bd=0, bg="#0a0e1a", fg=WHITE,
#                                    insertbackground=GOLD, selectbackground=GOLD)
#         self.user_entry.pack(padx=12, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_key)
#         self.user_entry.bind("<Return>",     self._on_enter)
#         self.user_entry.focus_set()

#         nc = tk.Frame(id_i, bg=CARD2)
#         nc.pack(fill=tk.X, pady=(10, 0))
#         self.name_lbl = tk.Label(nc, text="", font=("Courier", 15, "bold"),
#                                   bg=CARD2, fg=GREEN)
#         self.name_lbl.pack(anchor="w")
#         self.hint_lbl = tk.Label(nc, text="", font=("Courier", 9),
#                                   bg=CARD2, fg=MUTED)
#         self.hint_lbl.pack(anchor="w")

#         # STATUS BANNER
#         self.sf = tk.Frame(body, bg=ACCENT_DIM,
#                            highlightbackground=ACCENT, highlightthickness=1)
#         self.sf.pack(fill=tk.X, pady=(0, 16))
#         self.sl = tk.Label(self.sf, text="◉   Enter Worker ID to begin",
#                            font=("Courier", 10), bg=ACCENT_DIM, fg=ACCENT,
#                            pady=11, padx=16, anchor="w")
#         self.sl.pack(fill=tk.X)

#         # BUTTONS
#         br = tk.Frame(body, bg=BG)
#         br.pack(fill=tk.X, pady=(0, 16))

#         self.btn_in = tk.Button(br, text="▶   CHECK  IN",
#                                 font=("Courier", 12, "bold"), width=18,
#                                 relief=tk.FLAT, bg=GREEN_DIM, fg=MUTED,
#                                 activebackground=GREEN, activeforeground=BG,
#                                 cursor="hand2", state=tk.DISABLED,
#                                 command=lambda: self._trigger("checkin"))
#         self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         self.btn_out = tk.Button(br, text="◼   CHECK  OUT",
#                                  font=("Courier", 12, "bold"), width=18,
#                                  relief=tk.FLAT, bg=RED_DIM, fg=MUTED,
#                                  activebackground=RED, activeforeground=WHITE,
#                                  cursor="hand2", state=tk.DISABLED,
#                                  command=lambda: self._trigger("checkout"))
#         self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

#         tk.Button(br, text="✕ CLEAR", font=("Courier", 9, "bold"),
#                   relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                   activebackground=MUTED, activeforeground=WHITE,
#                   cursor="hand2", command=self._reset_ui
#                   ).pack(side=tk.LEFT, ipady=10)

#         # DIVIDER
#         tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

#         # LOG
#         lh = tk.Frame(body, bg=BG)
#         lh.pack(fill=tk.X, pady=(0, 6))
#         tk.Label(lh, text="ACTIVITY LOG", font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         tk.Button(lh, text="CLEAR LOG", font=("Courier", 7, "bold"),
#                   relief=tk.FLAT, bg=BORDER, fg=MUTED, padx=6, pady=2,
#                   cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

#         lw = tk.Frame(body, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
#         lw.pack(fill=tk.BOTH, expand=True)
#         sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD2)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(lw, font=("Courier", 10), bg=CARD2, fg=TEXT,
#                                relief=tk.FLAT, padx=12, pady=10,
#                                yscrollcommand=sb.set, state=tk.DISABLED)
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#         for tag, col in [("ok", GREEN), ("err", RED), ("warn", ORANGE),
#                          ("info", ACCENT), ("ts", MUTED), ("div", BORDER)]:
#             self.log_box.tag_config(tag, foreground=col)

#         # FLASH OVERLAY
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.fi = tk.Label(self.flash, font=("Courier", 64, "bold"), bg=ACCENT, fg=WHITE)
#         self.fi.place(relx=0.5, rely=0.35, anchor="center")
#         self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
#                            bg=ACCENT, fg=WHITE, wraplength=700)
#         self.fm.place(relx=0.5, rely=0.52, anchor="center")
#         self.fs = tk.Label(self.flash, font=("Courier", 13),
#                            bg=ACCENT, fg="#c7d9ff", wraplength=700)
#         self.fs.place(relx=0.5, rely=0.63, anchor="center")

#     # ── CLOCK ─────────────────────────────────────────────
#     def _tick_clock(self):
#         n = datetime.now()
#         self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
#         self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── LOGGING ───────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END,
#                 f"[{datetime.now().strftime('%H:%M:%S')}]  ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     # ── FLASH ─────────────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, color):
#         self.flash.config(bg=color)
#         for w, v in [(self.fi, icon), (self.fm, headline), (self.fs, sub)]:
#             w.config(text=v, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2000, self.flash.place_forget)

#     # ── STATUS & BUTTONS ──────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.sf.config(bg=bg, highlightbackground=border)
#             self.sl.config(text=text, fg=fg, bg=bg)
#         self.root.after(0, _do)

#     def _set_buttons(self, in_s, out_s):
#         def _do():
#             self.btn_in.config(
#                 state=in_s,
#                 bg=GREEN if in_s == tk.NORMAL else GREEN_DIM,
#                 fg=BG    if in_s == tk.NORMAL else MUTED)
#             self.btn_out.config(
#                 state=out_s,
#                 bg=RED   if out_s == tk.NORMAL else RED_DIM,
#                 fg=WHITE if out_s == tk.NORMAL else MUTED)
#         self.root.after(0, _do)

#     def _apply_status(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("◉   Attendance complete — see you tomorrow!",
#                              RED, RED_DIM, RED)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status("◉   Already CHECKED IN — proceed to Check-Out",
#                              ORANGE, ORANGE_DIM, ORANGE)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status("◉   Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("◉   Enter Worker ID to begin",
#                              ACCENT, ACCENT_DIM, ACCENT)

#     # ── ID VALIDATION (debounced, no fingerprint needed) ──
#     def _on_key(self, _=None):
#         if self._debounce_job:
#             self.root.after_cancel(self._debounce_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._soft_reset(); return
#         # Instant local status (from file)
#         self._apply_status(get_worker_status(uid))
#         # Delayed Zoho lookup after 700ms of no typing
#         self._debounce_job = self.root.after(
#             700, lambda: threading.Thread(
#                 target=self._validate, args=(uid,), daemon=True).start())

#     def _validate(self, uid):
#         """Silently validate ID against Zoho; update UI when done."""
#         if self.user_entry.get().strip() != uid or self._busy:
#             return
#         if uid in self._worker_cache:
#             worker = self._worker_cache[uid]
#         else:
#             worker = find_worker(uid)
#             if worker:
#                 self._worker_cache[uid] = worker

#         if self.user_entry.get().strip() != uid:
#             return

#         def _upd():
#             if not worker:
#                 self.name_lbl.config(text="", fg=RED)
#                 self.hint_lbl.config(
#                     text=f"✗  ID '{uid}' not found — contact admin", fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(f"◉   Worker ID {uid} does not exist",
#                                  RED, RED_DIM, RED)
#             else:
#                 name   = worker.get("Full_Name", "N/A")
#                 status = get_worker_status(uid)
#                 self.name_lbl.config(text=name, fg=GREEN)
#                 hints = {
#                     "checked_in": ("Already checked IN — use Check-Out ↓", ORANGE),
#                     "done":       ("Attendance complete for today", RED),
#                     "none":       ("Ready to check in", MUTED),
#                 }
#                 htxt, hcol = hints.get(status, ("", MUTED))
#                 self.hint_lbl.config(text=htxt, fg=hcol)
#                 self._apply_status(status)
#         self.root.after(0, _upd)

#     def _on_enter(self, _=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy: return
#         s = get_worker_status(uid)
#         if s == "none":        self._trigger("checkin")
#         elif s == "checked_in": self._trigger("checkout")

#     # ── TRIGGER ───────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy: return
#         uid = self.user_entry.get().strip()
#         if not uid: return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉   Scanning fingerprint...", ORANGE, ORANGE_DIM, ORANGE)
#         threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

#     # ── MAIN WORKER THREAD ────────────────────────────────
#     def _process(self, uid, action):
#         is_open  = False
#         success  = False
#         msg      = ""
#         full_name = uid

#         try:
#             self.log(f"{'─'*20} {action.upper()} · ID {uid} {'─'*20}", "div")

#             # ── Fingerprint device ───────────────────────
#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Connect the fingerprint device and try again.", "#7c3aed"))
#                 return

#             zk.OpenDevice(0)
#             is_open = True
#             self.log("Place your finger on the scanner...", "info")

#             capture = None
#             for _ in range(150):  # up to 30 s
#                 capture = zk.AcquireFingerprint()
#                 if capture: break
#                 time.sleep(0.2)

#             if not capture:
#                 self.log("Scan timed out — please try again", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout", "No fingerprint detected.", "#b45309"))
#                 return

#             self.log("Fingerprint captured ✔", "ok")

#             # ── Worker lookup ─────────────────────────────
#             worker = self._worker_cache.get(uid) or find_worker(uid)
#             if worker:
#                 self._worker_cache[uid] = worker
#             if not worker:
#                 self.log(f"ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found",
#                     f"ID {uid} does not exist in the system.", RED))
#                 return

#             full_name = worker.get("Full_Name", uid)
#             self.log(f"Worker: {full_name}", "ok")

#             # ── Guard checks ──────────────────────────────
#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log("Attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Done", full_name, "#7c3aed"))
#                 self.root.after(2200, lambda: self._apply_status("done"))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log("Already checked IN — redirecting to Check-Out", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In",
#                     f"{full_name} — please use Check-Out", "#92400e"))
#                 self.root.after(2200, lambda: self._apply_status("checked_in"))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log("Not checked IN yet — check in first", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In",
#                     f"{full_name} — check IN first", "#7c3aed"))
#                 self.root.after(2200, lambda: self._apply_status("none"))
#                 return

#             # ── Post to Zoho ──────────────────────────────
#             self.log(f"Posting {action.upper()} to Zoho...", "info")
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID

#             success, msg = log_attendance(
#                 worker["ID"], uid, pid, full_name, action)

#             tag = "ok" if success else "err"
#             for line in msg.splitlines():
#                 if line.strip():
#                     self.log(line.strip(), tag)

#             if success:
#                 verb = "Checked IN" if action == "checkin" else "Checked OUT"
#                 sub  = datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y")
#                 self.root.after(0, lambda: self._show_flash(
#                     "✔", f"{verb}  —  {full_name}", sub, "#1d4ed8"))
#             else:
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", msg.splitlines()[0][:80], RED))

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")

#         finally:
#             if is_open:
#                 try: zk.CloseDevice()
#                 except: pass
#             self._busy = False
#             # 2.2 s — flash finishes, then wipe everything for next worker
#             self.root.after(2200, lambda: self._reset_ui(clear_log=success))

#     # ── RESET ─────────────────────────────────────────────
#     def _reset_ui(self, clear_log=False):
#         """Clear all fields and optionally wipe the log for the next worker."""
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="")
#         self.hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉   Enter Worker ID to begin",
#                          ACCENT, ACCENT_DIM, ACCENT)
#         if clear_log:
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.delete("1.0", tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.log("Ready for next worker.", "div")
#         self.user_entry.focus_set()

#     def _soft_reset(self):
#         self.name_lbl.config(text="")
#         self.hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉   Enter Worker ID to begin",
#                          ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ─────────────────────────────────────────────
#     def _on_close(self):
#         try: zk.Terminate()
#         except: pass
#         self.root.destroy()


# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop()






# import os, time, json, csv, requests, threading
# from datetime import datetime, timedelta
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import ttk, messagebox

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ── Shift policy ────────────────────────────────────────────
# SHIFT_START_H  = 7       # 07:00 AM
# SHIFT_START_M  = 0
# SHIFT_HOURS    = 8       # standard hours before overtime kicks in
# GRACE_MINUTES  = 10      # 10-min grace period before "late" is flagged

# # ===========================================================
# # GLOBAL SDK
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, retries=3, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     for attempt in range(1, retries + 1):
#         try:
#             return requests.request(method, url, **kwargs)
#         except (requests.exceptions.Timeout,
#                 requests.exceptions.ConnectionError, OSError):
#             if attempt < retries:
#                 time.sleep(2 * attempt)
#     return None

# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
#         return TOKEN_CACHE["token"]
#     TOKEN_CACHE["token"] = None
#     url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
#     for _ in range(3):
#         r = zoho_request("POST", url, data=data, retries=1)
#         if r and r.status_code == 200:
#             res = r.json()
#             TOKEN_CACHE["token"]      = res.get("access_token")
#             TOKEN_CACHE["expires_at"] = now + int(res.get("expires_in", 3600))
#             return TOKEN_CACHE["token"]
#         time.sleep(3)
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#             if data.get("date") == today:
#                 return data
#         except Exception:
#             pass
#     fresh = {"date": today, "checked_in": {}, "checked_out": {}}
#     save_lock(fresh)
#     return fresh

# def save_lock(data):
#     tmp = CHECKIN_LOCK_FILE + ".tmp"
#     with open(tmp, "w") as f:
#         json.dump(data, f, indent=2)
#     os.replace(tmp, CHECKIN_LOCK_FILE)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     key  = str(zk_id)
#     if key in lock["checked_out"]: return "done"
#     if key in lock["checked_in"]:  return "checked_in"
#     return "none"

# # ===========================================================
# # SHIFT HELPERS
# # ===========================================================
# def is_late(checkin_dt):
#     """Return True if checkin_dt is past the grace window."""
#     cutoff = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0
#     ) + timedelta(minutes=GRACE_MINUTES)
#     return checkin_dt > cutoff

# def late_by_str(checkin_dt):
#     """Human-readable 'late by X min' string."""
#     shift_start = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0)
#     delta = max((checkin_dt - shift_start).total_seconds(), 0)
#     mins  = int(delta // 60)
#     return f"{mins} min late" if mins else "on time"

# def overtime_hours(total_hours):
#     """Return overtime hours (above SHIFT_HOURS), or 0."""
#     return max(round(total_hours - SHIFT_HOURS, 4), 0)

# # ===========================================================
# # ZOHO API
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def _extract_zoho_id(res_json):
#     data = res_json.get("data")
#     if isinstance(data, dict):
#         return data.get("ID") or data.get("id")
#     if isinstance(data, list) and data:
#         return data[0].get("ID") or data[0].get("id")
#     return res_json.get("ID") or res_json.get("id")

# def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs, _log=None):
#     """
#     Search Zoho for today's attendance record.
#     Tries worker-specific criteria first, then falls back to a
#     date-only fetch matched client-side — so it works regardless
#     of what the worker lookup field is called in your Zoho app.
#     _log: optional callable(msg, tag) for GUI diagnostic output.
#     """
#     def dbg(msg):
#         print(f"[ZOHO SEARCH] {msg}")
#         if _log: _log(f"[search] {msg}", "warn")

#     report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     dbg(f"worker_id={worker_id}  dates={today_display}/{today_iso}")

#     # ── Strategy 1: worker + date criteria (most specific) ──────────────
#     criteria_list = [
#         f'(Worker_Name == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_Name == "{worker_id}" && Date == "{today_iso}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
#         # Worker-only fallback (no date) — safe if only one record per day
#         f'(Worker_Name == "{worker_id}")',
#         f'(Worker_ID_Lookup == "{worker_id}")',
#     ]
#     for crit in criteria_list:
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if not r or r.status_code != 200:
#             dbg(f"  HTTP {r.status_code if r else 'timeout'} → {crit}")
#             continue
#         recs = r.json().get("data", [])
#         dbg(f"  {len(recs)} result(s) → {crit}")
#         if not recs:
#             continue
#         # Prefer an exact date match
#         for rec in recs:
#             d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
#             if d in (today_display, today_iso):
#                 dbg(f"  ✔ date-matched record ID={rec['ID']}")
#                 return rec["ID"]
#         # Single result with no date = almost certainly today's record
#         if len(recs) == 1:
#             dbg(f"  ✔ single-result fallback ID={recs[0]['ID']}")
#             return recs[0]["ID"]

#     # ── Strategy 2: date-only fetch, match worker client-side ───────────
#     # Works no matter what the worker lookup field is called in Zoho.
#     dbg("  Trying date-only broad search...")
#     for date_val in (today_display, today_iso):
#         r = zoho_request("GET", report_url, headers=hdrs,
#                          params={"criteria": f'(Date == "{date_val}")'})
#         if not r or r.status_code != 200:
#             continue
#         recs = r.json().get("data", [])
#         dbg(f"  date-only → {len(recs)} record(s) for {date_val}")
#         for rec in recs:
#             # Check every field that might hold the worker lookup ID
#             for field in ("Worker_Name", "Worker_ID_Lookup", "Worker",
#                           "Worker_Name.ID", "Worker_ID"):
#                 val = rec.get(field)
#                 if isinstance(val, dict):
#                     val = (val.get("ID") or val.get("id")
#                            or val.get("display_value", ""))
#                 if str(val).strip() == str(worker_id).strip():
#                     dbg(f"  ✔ client-matched via '{field}' → ID={rec['ID']}")
#                     return rec["ID"]
#         # Dump first record's keys/values so we can diagnose field names
#         if recs:
#             dbg(f"  First record keys: {list(recs[0].keys())}")
#             sample = {k: recs[0][k] for k in list(recs[0].keys())[:10]}
#             dbg(f"  First record sample: {sample}")

#     dbg("  ✗ All strategies exhausted — record not found.")
#     return None

# # ===========================================================
# # ATTENDANCE LOGIC
# # ===========================================================
# def log_attendance(worker_id, zk_id, project_id, full_name, action, _log=None):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     # ── CHECK-IN ─────────────────────────────────────────────
#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         hdrs         = auth_headers()
#         worker_late  = is_late(now)
#         late_note    = late_by_str(now)

#         payload = {"data": {
#             "Worker_Name":      worker_id,
#             "Projects":         project_id,
#             "Date":             today_display,
#             "First_In":         checkin_time,
#             "Worker_Full_Name": full_name,
#             "Is_Late":          "true" if worker_late else "false",
#             "Late_By_Minutes":  int(max((now - now.replace(
#                                     hour=SHIFT_START_H, minute=SHIFT_START_M,
#                                     second=0, microsecond=0)).total_seconds() // 60, 0))
#                                 if worker_late else 0,
#         }}

#         r = zoho_request("POST", form_url, headers=hdrs, json=payload)
#         if r and r.status_code in (200, 201):
#             res         = r.json()
#             zoho_rec_id = _extract_zoho_id(res)
#             if not zoho_rec_id:
#                 zoho_rec_id = _find_record_in_zoho(
#                     worker_id, today_display, today_iso, auth_headers(), _log)

#             lock = load_lock()
#             lock["checked_in"][zk_key] = {
#                 "time":      checkin_time,
#                 "zoho_id":   zoho_rec_id,
#                 "worker_id": worker_id,
#                 "name":      full_name,
#                 "is_late":   worker_late,
#                 "late_note": late_note,
#             }
#             save_lock(lock)

#             status_line = f"⚠ {late_note}" if worker_late else "✓ On time"
#             return True, (
#                 f"✅ {full_name} checked IN at {now.strftime('%H:%M')}\n"
#                 f"   {status_line}"
#             )

#         err = r.text[:200] if r else "Timeout"
#         return False, f"Check-in failed: {err}"

#     # ── CHECK-OUT ────────────────────────────────────────────
#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "No check-in record found for today."

#         hdrs = auth_headers()
#         if not hdrs:
#             return False, "Could not refresh Zoho token — check internet."

#         att_record_id = info.get("zoho_id")
#         stored_worker = info.get("worker_id", worker_id)

#         def dbg(msg):
#             print(f"[CHECKOUT] {msg}")
#             if _log: _log(f"[checkout] {msg}", "warn")

#         dbg(f"stored zoho_id={att_record_id}  stored_worker={stored_worker}")

#         # ── Step 1: verify the stored ID actually exists in Zoho ──────────
#         if att_record_id:
#             direct_url = (
#                 f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#                 f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
#             )
#             r_chk = zoho_request("GET", direct_url, headers=hdrs)
#             dbg(f"direct GET by ID → HTTP {r_chk.status_code if r_chk else 'timeout'}")
#             if r_chk and r_chk.status_code == 200:
#                 dbg("stored ID confirmed valid ✔")
#             else:
#                 # ID is stale / wrong — clear it and search
#                 dbg("stored ID invalid — clearing and searching...")
#                 att_record_id = None

#         # ── Step 2: report search (if no valid ID yet) ─────────────────────
#         if not att_record_id:
#             att_record_id = _find_record_in_zoho(
#                 stored_worker, today_display, today_iso, hdrs, _log)
#             if att_record_id:
#                 lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                 save_lock(lock)

#         # ── Step 3: no-criteria probe — expose what the report actually has ─
#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             r_all = zoho_request("GET", report_url, headers=hdrs,
#                                  params={"from": 1, "limit": 5})
#             if r_all and r_all.status_code == 200:
#                 all_recs = r_all.json().get("data", [])
#                 dbg(f"no-criteria probe → {len(all_recs)} record(s) in report")
#                 for i, rec in enumerate(all_recs):
#                     dbg(f"  rec[{i}] keys={list(rec.keys())}")
#                     dbg(f"  rec[{i}] sample={ {k: rec[k] for k in list(rec.keys())[:8]} }")
#             else:
#                 status = r_all.status_code if r_all else "timeout"
#                 body   = r_all.text[:300] if r_all else "no response"
#                 dbg(f"no-criteria probe failed → HTTP {status}: {body}")

#             # ── Step 4: try the FORM endpoint directly (different from report) ─
#             # Zoho reports can have filters; the form index has everything.
#             form_index_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#             for date_val in (today_display, today_iso):
#                 crit = f'(Worker_Name == "{stored_worker}" && Date == "{date_val}")'
#                 r_f = zoho_request("GET", form_index_url, headers=hdrs,
#                                    params={"criteria": crit})
#                 dbg(f"form GET ({date_val}) → HTTP {r_f.status_code if r_f else 'timeout'}")
#                 if r_f and r_f.status_code == 200:
#                     frecs = r_f.json().get("data", [])
#                     dbg(f"  form returned {len(frecs)} record(s)")
#                     if frecs:
#                         att_record_id = frecs[0].get("ID")
#                         dbg(f"  ✔ found via form endpoint → ID={att_record_id}")
#                         lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                         save_lock(lock)
#                         break

#         if not att_record_id:
#             return False, (
#                 f"Could not locate today's attendance record in Zoho.\n"
#                 f"Worker: {full_name}  Date: {today_display}\n"
#                 f"Stored Zoho ID: {info.get('zoho_id', 'None')}\n"
#                 "Check the terminal/log for [checkout] diagnostics.\n"
#                 "The record may not have been created at check-in time."
#             )

#         # Hours calculation
#         # NOTE: Total_Hours rounded to 2 decimal places to stay within
#         # Zoho's field digit limit (e.g. 99.99 max).
#         try:
#             dt_in = datetime.strptime(info.get("time", ""), "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)
#         ot_hours    = overtime_hours(total_hours)
#         total_str   = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"
#         ot_str      = f"{int(ot_hours)}h {int((ot_hours % 1) * 60)}m" if ot_hours else "None"

#         # Round to 2dp — Zoho rejects values with too many decimal digits
#         total_hours_rounded = round(total_hours, 2)
#         ot_hours_rounded    = round(ot_hours, 2)
#         dbg(f"hours: total={total_hours_rounded}  overtime={ot_hours_rounded}")

#         # ── PATCH ──────────────────────────────────────────────────────────
#         # Daily_Attendance_Report is confirmed writable (returned HTTP 200).
#         update_url = (
#             f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#             f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
#         )
#         dbg(f"PATCH → {ATTENDANCE_REPORT}/{att_record_id}")
#         r_u = zoho_request("PATCH", update_url, headers=hdrs, json={"data": {
#             "Last_Out":       now.strftime("%d-%b-%Y %H:%M:%S"),
#             "Total_Hours":    total_hours_rounded,
#             "Overtime_Hours": ot_hours_rounded,
#         }})

#         http_code = r_u.status_code if r_u else "timeout"
#         body_raw  = r_u.text[:300] if r_u else "No response"
#         dbg(f"PATCH result → HTTP {http_code}  body={body_raw}")

#         if r_u and r_u.status_code == 200:
#             body = r_u.json()
#             code = body.get("code")
#             if code == 3000:
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = {
#                     "time":           now.strftime("%H:%M:%S"),
#                     "name":           full_name,
#                     "total_hours":    total_hours_rounded,
#                     "overtime_hours": ot_hours_rounded,
#                     "is_late":        info.get("is_late", False),
#                     "late_note":      info.get("late_note", ""),
#                     "checkin_time":   info.get("time", ""),
#                 }
#                 save_lock(lock)
#                 ot_line = f"   Overtime: {ot_str}" if ot_hours else ""
#                 return True, (
#                     f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}\n"
#                     f"   Total time: {total_str}\n"
#                     f"{ot_line}"
#                 )
#             # Field validation or other Zoho error — surface the full message
#             errors = body.get("error", body.get("message", ""))
#             return False, (
#                 f"Zoho rejected the update (code {code}).\n"
#                 f"Error: {errors}\n"
#                 f"Worker: {full_name}  Hours sent: {total_hours_rounded}"
#             )

#         return False, f"Check-out PATCH failed (HTTP {http_code}): {body_raw}"

#     return False, "Unknown action."

# # ===========================================================
# # DAILY SUMMARY EXPORT
# # ===========================================================
# def export_daily_summary():
#     """Write today's attendance to a CSV and return the filename."""
#     lock     = load_lock()
#     today    = lock.get("date", datetime.now().strftime("%Y-%m-%d"))
#     filename = f"attendance_{today}.csv"

#     rows = []
#     # Checked-out workers (complete records)
#     for zk_id, info in lock.get("checked_out", {}).items():
#         rows.append({
#             "ZK_ID":          zk_id,
#             "Name":           info.get("name", ""),
#             "Check-In":       info.get("checkin_time", ""),
#             "Check-Out":      info.get("time", ""),
#             "Total Hours":    info.get("total_hours", ""),
#             "Overtime Hours": info.get("overtime_hours", 0),
#             "Late?":          "Yes" if info.get("is_late") else "No",
#             "Late Note":      info.get("late_note", ""),
#             "Status":         "Complete",
#         })
#     # Still checked-in workers
#     for zk_id, info in lock.get("checked_in", {}).items():
#         rows.append({
#             "ZK_ID":          zk_id,
#             "Name":           info.get("name", ""),
#             "Check-In":       info.get("time", ""),
#             "Check-Out":      "—",
#             "Total Hours":    "—",
#             "Overtime Hours": "—",
#             "Late?":          "Yes" if info.get("is_late") else "No",
#             "Late Note":      info.get("late_note", ""),
#             "Status":         "Still In",
#         })

#     if not rows:
#         return None

#     fieldnames = ["ZK_ID","Name","Check-In","Check-Out",
#                   "Total Hours","Overtime Hours","Late?","Late Note","Status"]
#     with open(filename, "w", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(rows)
#     return filename

# # ===========================================================
# # COLOUR PALETTE
# # ===========================================================
# BG         = "#060810"
# CARD       = "#0d1117"
# CARD2      = "#111827"
# BORDER     = "#1e2433"
# ACCENT     = "#3b82f6"
# ACCENT_DIM = "#1d3a6e"
# GREEN      = "#10b981"
# GREEN_DIM  = "#064e35"
# RED        = "#ef4444"
# RED_DIM    = "#450a0a"
# ORANGE     = "#f59e0b"
# ORANGE_DIM = "#451a03"
# TEXT       = "#f1f5f9"
# MUTED      = "#475569"
# WHITE      = "#ffffff"
# GOLD       = "#fbbf24"
# PURPLE     = "#8b5cf6"
# PURPLE_DIM = "#3b0764"

# # ===========================================================
# # ADMIN PANEL WINDOW
# # ===========================================================
# class AdminPanel(tk.Toplevel):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.title("Admin Panel — Today's Attendance")
#         self.configure(bg=BG)
#         self.resizable(True, True)
#         sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
#         W, H   = min(sw, 1000), min(sh, 600)
#         self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
#         self._build()
#         self.refresh()

#     def _build(self):
#         # Title bar
#         hdr = tk.Frame(self, bg=CARD, padx=20, pady=12)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=PURPLE, height=3).pack(fill=tk.X)  # not reachable — fixed below
#         tk.Label(hdr, text="ADMIN PANEL — TODAY'S ATTENDANCE",
#                  font=("Courier", 12, "bold"), bg=CARD, fg=PURPLE).pack(anchor="w", pady=(8,0))
#         self.sub_lbl = tk.Label(hdr, text="", font=("Courier", 8), bg=CARD, fg=MUTED)
#         self.sub_lbl.pack(anchor="w")

#         # Stats bar
#         self.stats_fr = tk.Frame(self, bg=BG, padx=20, pady=10)
#         self.stats_fr.pack(fill=tk.X)

#         # Treeview
#         tree_fr = tk.Frame(self, bg=CARD2, padx=12, pady=12)
#         tree_fr.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,10))

#         style = ttk.Style(self)
#         style.theme_use("default")
#         style.configure("Admin.Treeview",
#                         background=CARD2, foreground=TEXT,
#                         fieldbackground=CARD2, rowheight=26,
#                         font=("Courier", 9))
#         style.configure("Admin.Treeview.Heading",
#                         background=BORDER, foreground=GOLD,
#                         font=("Courier", 9, "bold"))
#         style.map("Admin.Treeview", background=[("selected", ACCENT_DIM)])

#         cols = ("Name","Check-In","Check-Out","Hours","Overtime","Late?","Status")
#         self.tree = ttk.Treeview(tree_fr, columns=cols, show="headings",
#                                   style="Admin.Treeview")
#         widths    = (180, 130, 130, 80, 90, 60, 90)
#         for col, w in zip(cols, widths):
#             self.tree.heading(col, text=col)
#             self.tree.column(col, width=w, anchor="center")
#         self.tree.tag_configure("late",     foreground=ORANGE)
#         self.tree.tag_configure("ot",       foreground=PURPLE)
#         self.tree.tag_configure("complete", foreground=GREEN)
#         self.tree.tag_configure("still_in", foreground=ACCENT)

#         vsb = ttk.Scrollbar(tree_fr, orient="vertical", command=self.tree.yview)
#         self.tree.configure(yscrollcommand=vsb.set)
#         self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         vsb.pack(side=tk.RIGHT, fill=tk.Y)

#         # Buttons
#         btn_fr = tk.Frame(self, bg=BG, padx=20, pady=8)
#         btn_fr.pack(fill=tk.X)
#         tk.Button(btn_fr, text="↻  REFRESH", font=("Courier", 9, "bold"),
#                   relief=tk.FLAT, bg=ACCENT_DIM, fg=ACCENT,
#                   activebackground=ACCENT, activeforeground=WHITE,
#                   cursor="hand2", padx=12, pady=6,
#                   command=self.refresh).pack(side=tk.LEFT, padx=(0,8))
#         tk.Button(btn_fr, text="⬇  EXPORT CSV", font=("Courier", 9, "bold"),
#                   relief=tk.FLAT, bg=GREEN_DIM, fg=GREEN,
#                   activebackground=GREEN, activeforeground=BG,
#                   cursor="hand2", padx=12, pady=6,
#                   command=self._export).pack(side=tk.LEFT)
#         tk.Button(btn_fr, text="✕  CLOSE", font=("Courier", 9, "bold"),
#                   relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                   cursor="hand2", padx=12, pady=6,
#                   command=self.destroy).pack(side=tk.RIGHT)

#     def refresh(self):
#         for row in self.tree.get_children():
#             self.tree.delete(row)

#         lock        = load_lock()
#         checked_in  = lock.get("checked_in", {})
#         checked_out = lock.get("checked_out", {})
#         total = len(checked_in) + len(checked_out)
#         late_count  = 0
#         ot_count    = 0

#         # Completed
#         for zk_id, info in checked_out.items():
#             name    = info.get("name", zk_id)
#             ci      = info.get("checkin_time", "—")
#             co      = info.get("time", "—")
#             hrs     = info.get("total_hours", 0)
#             ot      = info.get("overtime_hours", 0)
#             late    = info.get("is_late", False)
#             hrs_str = f"{int(hrs)}h {int((hrs%1)*60)}m" if isinstance(hrs, float) else str(hrs)
#             ot_str  = f"{int(ot)}h {int((ot%1)*60)}m" if ot else "—"
#             if late:     late_count += 1
#             if ot > 0:   ot_count   += 1
#             tags = []
#             if late:   tags.append("late")
#             if ot > 0: tags.append("ot")
#             tags.append("complete")
#             self.tree.insert("", tk.END,
#                              values=(name, ci[-8:] if len(ci)>8 else ci,
#                                      co, hrs_str, ot_str,
#                                      "⚠ Yes" if late else "No", "✔ Done"),
#                              tags=tuple(tags))

#         # Still in
#         now = datetime.now()
#         for zk_id, info in checked_in.items():
#             name = info.get("name", zk_id)
#             ci   = info.get("time", "—")
#             late = info.get("is_late", False)
#             # Live hours so far
#             try:
#                 dt_in    = datetime.strptime(ci, "%d-%b-%Y %H:%M:%S")
#                 hrs_so_far = (now - dt_in).total_seconds() / 3600
#                 hrs_str  = f"{int(hrs_so_far)}h {int((hrs_so_far%1)*60)}m"
#             except Exception:
#                 hrs_str = "—"
#             if late: late_count += 1
#             tags = ["late"] if late else []
#             tags.append("still_in")
#             self.tree.insert("", tk.END,
#                              values=(name, ci[-8:] if len(ci)>8 else ci,
#                                      "—", hrs_str, "—",
#                                      "⚠ Yes" if late else "No", "🕐 In"),
#                              tags=tuple(tags))

#         # Stats bar update
#         for w in self.stats_fr.winfo_children():
#             w.destroy()
#         for label, val, col in [
#             ("TOTAL", total, WHITE),
#             ("CHECKED OUT", len(checked_out), GREEN),
#             ("STILL IN",    len(checked_in),  ACCENT),
#             ("LATE",        late_count,        ORANGE),
#             ("OVERTIME",    ot_count,          PURPLE),
#         ]:
#             box = tk.Frame(self.stats_fr, bg=CARD2, padx=16, pady=8,
#                            highlightbackground=BORDER, highlightthickness=1)
#             box.pack(side=tk.LEFT, padx=(0,8))
#             tk.Label(box, text=str(val), font=("Courier", 20, "bold"),
#                      bg=CARD2, fg=col).pack()
#             tk.Label(box, text=label, font=("Courier", 7, "bold"),
#                      bg=CARD2, fg=MUTED).pack()

#         self.sub_lbl.config(
#             text=f"Date: {lock.get('date','')}  ·  "
#                  f"Shift: {SHIFT_START_H:02d}:{SHIFT_START_M:02d}  ·  "
#                  f"Standard: {SHIFT_HOURS}h  ·  "
#                  f"Grace: {GRACE_MINUTES} min  ·  "
#                  f"Last refreshed: {now.strftime('%H:%M:%S')}"
#         )

#     def _export(self):
#         fname = export_daily_summary()
#         if fname:
#             messagebox.showinfo("Export Complete",
#                                 f"Saved to:\n{os.path.abspath(fname)}", parent=self)
#         else:
#             messagebox.showwarning("Nothing to Export",
#                                    "No attendance records found for today.", parent=self)


# # ===========================================================
# # MAIN GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Real Estate Wages System")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy          = False
#         self._debounce_job  = None
#         self._worker_cache  = {}
#         sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
#         W, H   = min(sw, 860), min(sh, 720)
#         self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
#         self._build_ui()
#         self._tick_clock()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD ──────────────────────────────────────────────
#     def _build_ui(self):
#         # HEADER
#         hdr = tk.Frame(self.root, bg=CARD)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)
#         hi = tk.Frame(hdr, bg=CARD, padx=28, pady=14)
#         hi.pack(fill=tk.X)
#         lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="REAL ESTATE WAGES SYSTEM",
#                  font=("Courier", 14, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(lf, text="Wavemark Properties Limited · Attendance Terminal",
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2,0))

#         rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
#         # Admin button in header
#         tk.Button(rf, text="⚙ ADMIN", font=("Courier", 8, "bold"),
#                   relief=tk.FLAT, bg=PURPLE_DIM, fg=PURPLE,
#                   activebackground=PURPLE, activeforeground=WHITE,
#                   cursor="hand2", padx=8, pady=4,
#                   command=self._open_admin).pack(anchor="e", pady=(0,6))
#         self.date_lbl  = tk.Label(rf, text="", font=("Courier", 9), bg=CARD, fg=MUTED)
#         self.date_lbl.pack(anchor="e")
#         self.clock_lbl = tk.Label(rf, text="", font=("Courier", 22, "bold"), bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")

#         # SHIFT INFO STRIP
#         shift_info = (
#             f"Shift: {SHIFT_START_H:02d}:{SHIFT_START_M:02d}  ·  "
#             f"Standard: {SHIFT_HOURS}h  ·  "
#             f"Grace period: {GRACE_MINUTES} min"
#         )
#         tk.Label(self.root, text=shift_info, font=("Courier", 8),
#                  bg=CARD2, fg=MUTED, pady=4).pack(fill=tk.X)

#         # BODY
#         body = tk.Frame(self.root, bg=BG, padx=32, pady=16)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ID CARD
#         id_card = tk.Frame(body, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 14))
#         id_i = tk.Frame(id_card, bg=CARD2, padx=20, pady=14)
#         id_i.pack(fill=tk.X)
#         tk.Label(id_i, text="WORKER ID", font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED).pack(anchor="w")
#         er = tk.Frame(id_i, bg=CARD2); er.pack(fill=tk.X, pady=(6,0))
#         eb = tk.Frame(er, bg=GOLD, padx=2, pady=2); eb.pack(side=tk.LEFT)
#         ei = tk.Frame(eb, bg="#0a0e1a"); ei.pack()
#         self.user_entry = tk.Entry(ei, font=("Courier", 26, "bold"), width=10,
#                                    bd=0, bg="#0a0e1a", fg=WHITE,
#                                    insertbackground=GOLD, selectbackground=GOLD)
#         self.user_entry.pack(padx=12, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_key)
#         self.user_entry.bind("<Return>",     self._on_enter)
#         self.user_entry.focus_set()
#         nc = tk.Frame(id_i, bg=CARD2); nc.pack(fill=tk.X, pady=(8,0))
#         self.name_lbl = tk.Label(nc, text="", font=("Courier", 15, "bold"),
#                                   bg=CARD2, fg=GREEN)
#         self.name_lbl.pack(anchor="w")
#         self.hint_lbl = tk.Label(nc, text="", font=("Courier", 9), bg=CARD2, fg=MUTED)
#         self.hint_lbl.pack(anchor="w")

#         # STATUS BANNER
#         self.sf = tk.Frame(body, bg=ACCENT_DIM,
#                             highlightbackground=ACCENT, highlightthickness=1)
#         self.sf.pack(fill=tk.X, pady=(0, 14))
#         self.sl = tk.Label(self.sf, text="◉ Enter Worker ID to begin",
#                            font=("Courier", 10), bg=ACCENT_DIM, fg=ACCENT,
#                            pady=10, padx=16, anchor="w")
#         self.sl.pack(fill=tk.X)

#         # BUTTONS
#         br = tk.Frame(body, bg=BG); br.pack(fill=tk.X, pady=(0, 14))
#         self.btn_in = tk.Button(br, text="▶  CHECK IN",
#                                 font=("Courier", 12, "bold"), width=18, relief=tk.FLAT,
#                                 bg=GREEN_DIM, fg=MUTED, activebackground=GREEN,
#                                 activeforeground=BG, cursor="hand2", state=tk.DISABLED,
#                                 command=lambda: self._trigger("checkin"))
#         self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0,12))
#         self.btn_out = tk.Button(br, text="◼  CHECK OUT",
#                                  font=("Courier", 12, "bold"), width=18, relief=tk.FLAT,
#                                  bg=RED_DIM, fg=MUTED, activebackground=RED,
#                                  activeforeground=WHITE, cursor="hand2", state=tk.DISABLED,
#                                  command=lambda: self._trigger("checkout"))
#         self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0,12))
#         tk.Button(br, text="✕  CLEAR", font=("Courier", 9, "bold"), relief=tk.FLAT,
#                   bg=BORDER, fg=MUTED, activebackground=MUTED, activeforeground=WHITE,
#                   cursor="hand2", command=self._reset_ui
#                   ).pack(side=tk.LEFT, ipady=10)
#         tk.Button(br, text="⬇  EXPORT", font=("Courier", 9, "bold"), relief=tk.FLAT,
#                   bg=GREEN_DIM, fg=GREEN, activebackground=GREEN, activeforeground=BG,
#                   cursor="hand2", command=self._quick_export
#                   ).pack(side=tk.RIGHT, ipady=10)

#         # DIVIDER
#         tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0,10))

#         # LOG
#         lh = tk.Frame(body, bg=BG); lh.pack(fill=tk.X, pady=(0,6))
#         tk.Label(lh, text="ACTIVITY LOG", font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         tk.Button(lh, text="CLEAR LOG", font=("Courier", 7, "bold"), relief=tk.FLAT,
#                   bg=BORDER, fg=MUTED, padx=6, pady=2, cursor="hand2",
#                   command=self._clear_log).pack(side=tk.RIGHT)
#         lw = tk.Frame(body, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
#         lw.pack(fill=tk.BOTH, expand=True)
#         sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD2)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(lw, font=("Courier", 10), bg=CARD2, fg=TEXT,
#                                relief=tk.FLAT, padx=12, pady=10,
#                                yscrollcommand=sb.set, state=tk.DISABLED)
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)
#         for tag, col in [("ok", GREEN), ("err", RED), ("warn", ORANGE),
#                          ("info", ACCENT), ("ts", MUTED), ("div", BORDER),
#                          ("late", ORANGE), ("ot", PURPLE)]:
#             self.log_box.tag_config(tag, foreground=col)

#         # FLASH OVERLAY
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.fi = tk.Label(self.flash, font=("Courier", 64, "bold"), bg=ACCENT, fg=WHITE)
#         self.fi.place(relx=0.5, rely=0.30, anchor="center")
#         self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
#                            bg=ACCENT, fg=WHITE, wraplength=700)
#         self.fm.place(relx=0.5, rely=0.46, anchor="center")
#         self.fs = tk.Label(self.flash, font=("Courier", 13),
#                            bg=ACCENT, fg="#c7d9ff", wraplength=700)
#         self.fs.place(relx=0.5, rely=0.57, anchor="center")
#         self.fx = tk.Label(self.flash, font=("Courier", 11, "bold"),
#                            bg=ACCENT, fg=GOLD, wraplength=700)
#         self.fx.place(relx=0.5, rely=0.66, anchor="center")

#     # ── CLOCK ──────────────────────────────────────────────
#     def _tick_clock(self):
#         n = datetime.now()
#         self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
#         self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── ADMIN ──────────────────────────────────────────────
#     def _open_admin(self):
#         AdminPanel(self.root)

#     # ── QUICK EXPORT ───────────────────────────────────────
#     def _quick_export(self):
#         fname = export_daily_summary()
#         if fname:
#             self.log(f"Exported: {os.path.abspath(fname)}", "ok")
#         else:
#             self.log("Nothing to export — no records today.", "warn")

#     # ── LOGGING ────────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     # ── FLASH ──────────────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, extra, color):
#         self.flash.config(bg=color)
#         for w, v in [(self.fi, icon), (self.fm, headline),
#                      (self.fs, sub), (self.fx, extra)]:
#             w.config(text=v, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2200, self.flash.place_forget)

#     # ── STATUS & BUTTONS ───────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.sf.config(bg=bg, highlightbackground=border)
#             self.sl.config(text=text, fg=fg, bg=bg)
#         self.root.after(0, _do)

#     def _set_buttons(self, in_s, out_s):
#         def _do():
#             self.btn_in.config(
#                 state=in_s,
#                 bg=GREEN if in_s == tk.NORMAL else GREEN_DIM,
#                 fg=BG    if in_s == tk.NORMAL else MUTED)
#             self.btn_out.config(
#                 state=out_s,
#                 bg=RED   if out_s == tk.NORMAL else RED_DIM,
#                 fg=WHITE if out_s == tk.NORMAL else MUTED)
#         self.root.after(0, _do)

#     def _apply_status(self, status):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("◉ Attendance complete — see you tomorrow!", RED, RED_DIM, RED)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status("◉ Already CHECKED IN — proceed to Check-Out",
#                              ORANGE, ORANGE_DIM, ORANGE)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status("◉ Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("◉ Enter Worker ID to begin", ACCENT, ACCENT_DIM, ACCENT)

#     # ── ID VALIDATION ──────────────────────────────────────
#     def _on_key(self, _=None):
#         if self._debounce_job:
#             self.root.after_cancel(self._debounce_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._soft_reset(); return
#         self._apply_status(get_worker_status(uid))
#         self._debounce_job = self.root.after(
#             700, lambda: threading.Thread(
#                 target=self._validate, args=(uid,), daemon=True).start())

#     def _validate(self, uid):
#         if self.user_entry.get().strip() != uid or self._busy:
#             return
#         worker = self._worker_cache.get(uid) or find_worker(uid)
#         if worker:
#             self._worker_cache[uid] = worker
#         if self.user_entry.get().strip() != uid:
#             return
#         def _upd():
#             if not worker:
#                 self.name_lbl.config(text="", fg=RED)
#                 self.hint_lbl.config(
#                     text=f"✗ ID '{uid}' not found — contact admin", fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(f"◉ Worker ID {uid} does not exist",
#                                  RED, RED_DIM, RED)
#             else:
#                 name   = worker.get("Full_Name", "N/A")
#                 status = get_worker_status(uid)
#                 self.name_lbl.config(text=name, fg=GREEN)
#                 hints = {
#                     "checked_in": ("Already checked IN — use Check-Out ↓", ORANGE),
#                     "done":       ("Attendance complete for today",          RED),
#                     "none":       ("Ready to check in",                      MUTED),
#                 }
#                 htxt, hcol = hints.get(status, ("", MUTED))
#                 self.hint_lbl.config(text=htxt, fg=hcol)
#                 self._apply_status(status)
#         self.root.after(0, _upd)

#     def _on_enter(self, _=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy: return
#         s = get_worker_status(uid)
#         if s == "none":         self._trigger("checkin")
#         elif s == "checked_in": self._trigger("checkout")

#     # ── TRIGGER ────────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy: return
#         uid = self.user_entry.get().strip()
#         if not uid: return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉ Scanning fingerprint...", ORANGE, ORANGE_DIM, ORANGE)
#         threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

#     # ── MAIN WORKER THREAD ─────────────────────────────────
#     def _process(self, uid, action):
#         is_open   = False
#         success   = False
#         msg       = ""
#         full_name = uid
#         try:
#             self.log(f"{'─'*20} {action.upper()} · ID {uid} {'─'*20}", "div")

#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Connect the fingerprint device and try again.", "", "#7c3aed"))
#                 return

#             zk.OpenDevice(0); is_open = True
#             self.log("Place your finger on the scanner...", "info")
#             capture = None
#             for _ in range(150):
#                 capture = zk.AcquireFingerprint()
#                 if capture: break
#                 time.sleep(0.2)

#             if not capture:
#                 self.log("Scan timed out — please try again", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout", "No fingerprint detected.", "", "#b45309"))
#                 return

#             self.log("Fingerprint captured ✔", "ok")

#             worker = self._worker_cache.get(uid) or find_worker(uid)
#             if worker: self._worker_cache[uid] = worker
#             if not worker:
#                 self.log(f"ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found",
#                     f"ID {uid} does not exist in the system.", "", RED))
#                 return

#             full_name = worker.get("Full_Name", uid)
#             self.log(f"Worker: {full_name}", "ok")

#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log("Attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Done", full_name, "", "#7c3aed"))
#                 self.root.after(2400, lambda: self._apply_status("done"))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log("Already checked IN — redirect to Check-Out", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In",
#                     f"{full_name} — please use Check-Out", "", "#92400e"))
#                 self.root.after(2400, lambda: self._apply_status("checked_in"))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log("Not checked IN yet", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In",
#                     f"{full_name} — check IN first", "", "#7c3aed"))
#                 self.root.after(2400, lambda: self._apply_status("none"))
#                 return

#             self.log(f"Posting {action.upper()} to Zoho...", "info")
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID
#             success, msg = log_attendance(worker["ID"], uid, pid, full_name, action, self.log)

#             tag = "ok" if success else "err"
#             for line in msg.splitlines():
#                 if line.strip():
#                     # Tag late/overtime lines differently for visibility
#                     ltag = tag
#                     if "late" in line.lower():   ltag = "late"
#                     if "overtime" in line.lower(): ltag = "ot"
#                     self.log(line.strip(), ltag)

#             if success:
#                 verb = "Checked IN" if action == "checkin" else "Checked OUT"
#                 sub  = datetime.now().strftime("Time: %H:%M:%S · %A, %d %B %Y")

#                 # Build extra info line for flash
#                 extra = ""
#                 if action == "checkin" and is_late(datetime.now()):
#                     extra = f"⚠ Late arrival — {late_by_str(datetime.now())}"
#                 if action == "checkout":
#                     lock = load_lock()
#                     co   = lock.get("checked_out", {}).get(str(uid), {})
#                     ot   = co.get("overtime_hours", 0) if isinstance(co, dict) else 0
#                     if ot > 0:
#                         extra = f"⏱ Overtime: {int(ot)}h {int((ot%1)*60)}m"

#                 flash_color = "#1d4ed8"
#                 if action == "checkin" and is_late(datetime.now()):
#                     flash_color = "#92400e"

#                 _verb  = verb
#                 _sub   = sub
#                 _extra = extra
#                 _fc    = flash_color
#                 self.root.after(0, lambda: self._show_flash(
#                     "✔", f"{_verb} — {full_name}", _sub, _extra, _fc))
#             else:
#                 _m = msg.splitlines()[0][:80]
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", _m, "", RED))

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")
#         finally:
#             if is_open:
#                 try: zk.CloseDevice()
#                 except: pass
#             self._busy = False
#             self.root.after(2400, lambda: self._reset_ui(clear_log=success))

#     # ── RESET ──────────────────────────────────────────────
#     def _reset_ui(self, clear_log=False):
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="")
#         self.hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉ Enter Worker ID to begin", ACCENT, ACCENT_DIM, ACCENT)
#         if clear_log:
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.delete("1.0", tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.log("Ready for next worker.", "div")
#         self.user_entry.focus_set()

#     def _soft_reset(self):
#         self.name_lbl.config(text="")
#         self.hint_lbl.config(text="")
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("◉ Enter Worker ID to begin", ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ──────────────────────────────────────────────
#     def _on_close(self):
#         try: zk.Terminate()
#         except: pass
#         self.root.destroy()


# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop()





# import os, time, json, csv, requests, threading
# from datetime import datetime, timedelta
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import ttk, messagebox

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER          = "wavemarkpropertieslimited"
# APP_NAME           = "real-estate-wages-system"
# CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT     = "All_Workers"
# ATTENDANCE_FORM    = "Daily_Attendance"
# ATTENDANCE_REPORT  = "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE        = {"token": None, "expires_at": 0}
# API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE  = "checkin_today.json"

# # ── Shift policy ────────────────────────────────────────────
# SHIFT_START_H  = 7       # 07:00 AM
# SHIFT_START_M  = 0
# SHIFT_HOURS    = 8       # standard hours before overtime kicks in
# GRACE_MINUTES  = 10      # 10-min grace period before "late" is flagged

# # ===========================================================
# # GLOBAL SDK
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, retries=3, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     for attempt in range(1, retries + 1):
#         try:
#             return requests.request(method, url, **kwargs)
#         except (requests.exceptions.Timeout,
#                 requests.exceptions.ConnectionError, OSError):
#             if attempt < retries:
#                 time.sleep(2 * attempt)
#     return None

# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
#         return TOKEN_CACHE["token"]
#     TOKEN_CACHE["token"] = None
#     url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
#     for _ in range(3):
#         r = zoho_request("POST", url, data=data, retries=1)
#         if r and r.status_code == 200:
#             res = r.json()
#             TOKEN_CACHE["token"]      = res.get("access_token")
#             TOKEN_CACHE["expires_at"] = now + int(res.get("expires_in", 3600))
#             return TOKEN_CACHE["token"]
#         time.sleep(3)
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#             if data.get("date") == today:
#                 return data
#         except Exception:
#             pass
#     fresh = {"date": today, "checked_in": {}, "checked_out": {}}
#     save_lock(fresh)
#     return fresh

# def save_lock(data):
#     tmp = CHECKIN_LOCK_FILE + ".tmp"
#     with open(tmp, "w") as f:
#         json.dump(data, f, indent=2)
#     os.replace(tmp, CHECKIN_LOCK_FILE)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     key  = str(zk_id)
#     if key in lock["checked_out"]: return "done"
#     if key in lock["checked_in"]:  return "checked_in"
#     return "none"

# # ===========================================================
# # SHIFT HELPERS
# # ===========================================================
# def is_late(checkin_dt):
#     """Return True if checkin_dt is past the grace window."""
#     cutoff = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0
#     ) + timedelta(minutes=GRACE_MINUTES)
#     return checkin_dt > cutoff

# def late_by_str(checkin_dt):
#     """Human-readable 'late by X min' string."""
#     shift_start = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0)
#     delta = max((checkin_dt - shift_start).total_seconds(), 0)
#     mins  = int(delta // 60)
#     return f"{mins} min late" if mins else "on time"

# def overtime_hours(total_hours):
#     """Return overtime hours (above SHIFT_HOURS), or 0."""
#     return max(round(total_hours - SHIFT_HOURS, 4), 0)

# # ===========================================================
# # ZOHO API
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def _extract_zoho_id(res_json):
#     data = res_json.get("data")
#     if isinstance(data, dict):
#         return data.get("ID") or data.get("id")
#     if isinstance(data, list) and data:
#         return data[0].get("ID") or data[0].get("id")
#     return res_json.get("ID") or res_json.get("id")

# def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs, _log=None):
#     """
#     Search Zoho for today's attendance record.
#     Tries worker-specific criteria first, then falls back to a
#     date-only fetch matched client-side — so it works regardless
#     of what the worker lookup field is called in your Zoho app.
#     _log: optional callable(msg, tag) for GUI diagnostic output.
#     """
#     def dbg(msg):
#         print(f"[ZOHO SEARCH] {msg}")
#         if _log: _log(f"[search] {msg}", "warn")

#     report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     dbg(f"worker_id={worker_id}  dates={today_display}/{today_iso}")

#     # ── Strategy 1: worker + date criteria (most specific) ──────────────
#     criteria_list = [
#         f'(Worker_Name == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_Name == "{worker_id}" && Date == "{today_iso}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
#         # Worker-only fallback (no date) — safe if only one record per day
#         f'(Worker_Name == "{worker_id}")',
#         f'(Worker_ID_Lookup == "{worker_id}")',
#     ]
#     for crit in criteria_list:
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if not r or r.status_code != 200:
#             dbg(f"  HTTP {r.status_code if r else 'timeout'} → {crit}")
#             continue
#         recs = r.json().get("data", [])
#         dbg(f"  {len(recs)} result(s) → {crit}")
#         if not recs:
#             continue
#         # Prefer an exact date match
#         for rec in recs:
#             d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
#             if d in (today_display, today_iso):
#                 dbg(f"  ✔ date-matched record ID={rec['ID']}")
#                 return rec["ID"]
#         # Single result with no date = almost certainly today's record
#         if len(recs) == 1:
#             dbg(f"  ✔ single-result fallback ID={recs[0]['ID']}")
#             return recs[0]["ID"]

#     # ── Strategy 2: date-only fetch, match worker client-side ───────────
#     # Works no matter what the worker lookup field is called in Zoho.
#     dbg("  Trying date-only broad search...")
#     for date_val in (today_display, today_iso):
#         r = zoho_request("GET", report_url, headers=hdrs,
#                          params={"criteria": f'(Date == "{date_val}")'})
#         if not r or r.status_code != 200:
#             continue
#         recs = r.json().get("data", [])
#         dbg(f"  date-only → {len(recs)} record(s) for {date_val}")
#         for rec in recs:
#             # Check every field that might hold the worker lookup ID
#             for field in ("Worker_Name", "Worker_ID_Lookup", "Worker",
#                           "Worker_Name.ID", "Worker_ID"):
#                 val = rec.get(field)
#                 if isinstance(val, dict):
#                     val = (val.get("ID") or val.get("id")
#                            or val.get("display_value", ""))
#                 if str(val).strip() == str(worker_id).strip():
#                     dbg(f"  ✔ client-matched via '{field}' → ID={rec['ID']}")
#                     return rec["ID"]
#         # Dump first record's keys/values so we can diagnose field names
#         if recs:
#             dbg(f"  First record keys: {list(recs[0].keys())}")
#             sample = {k: recs[0][k] for k in list(recs[0].keys())[:10]}
#             dbg(f"  First record sample: {sample}")

#     dbg("  ✗ All strategies exhausted — record not found.")
#     return None

# # ===========================================================
# # ATTENDANCE LOGIC
# # ===========================================================
# def log_attendance(worker_id, zk_id, project_id, full_name, action, _log=None):
#     now           = datetime.now()
#     zk_key        = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     # ── CHECK-IN ─────────────────────────────────────────────
#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         hdrs         = auth_headers()
#         worker_late  = is_late(now)
#         late_note    = late_by_str(now)

#         payload = {"data": {
#             "Worker_Name":      worker_id,
#             "Projects":         project_id,
#             "Date":             today_display,
#             "First_In":         checkin_time,
#             "Worker_Full_Name": full_name,
#             "Is_Late":          "true" if worker_late else "false",
#             "Late_By_Minutes":  int(max((now - now.replace(
#                                     hour=SHIFT_START_H, minute=SHIFT_START_M,
#                                     second=0, microsecond=0)).total_seconds() // 60, 0))
#                                 if worker_late else 0,
#         }}

#         r = zoho_request("POST", form_url, headers=hdrs, json=payload)
#         if r and r.status_code in (200, 201):
#             res         = r.json()
#             zoho_rec_id = _extract_zoho_id(res)
#             if not zoho_rec_id:
#                 zoho_rec_id = _find_record_in_zoho(
#                     worker_id, today_display, today_iso, auth_headers(), _log)

#             lock = load_lock()
#             lock["checked_in"][zk_key] = {
#                 "time":      checkin_time,
#                 "zoho_id":   zoho_rec_id,
#                 "worker_id": worker_id,
#                 "name":      full_name,
#                 "is_late":   worker_late,
#                 "late_note": late_note,
#             }
#             save_lock(lock)

#             status_line = f"⚠ {late_note}" if worker_late else "✓ On time"
#             return True, (
#                 f"✅ {full_name} checked IN at {now.strftime('%H:%M')}\n"
#                 f"   {status_line}"
#             )

#         err = r.text[:200] if r else "Timeout"
#         return False, f"Check-in failed: {err}"

#     # ── CHECK-OUT ────────────────────────────────────────────
#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "No check-in record found for today."

#         hdrs = auth_headers()
#         if not hdrs:
#             return False, "Could not refresh Zoho token — check internet."

#         att_record_id = info.get("zoho_id")
#         stored_worker = info.get("worker_id", worker_id)

#         def dbg(msg):
#             print(f"[CHECKOUT] {msg}")
#             if _log: _log(f"[checkout] {msg}", "warn")

#         dbg(f"stored zoho_id={att_record_id}  stored_worker={stored_worker}")

#         # ── Step 1: verify the stored ID actually exists in Zoho ──────────
#         if att_record_id:
#             direct_url = (
#                 f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#                 f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
#             )
#             r_chk = zoho_request("GET", direct_url, headers=hdrs)
#             dbg(f"direct GET by ID → HTTP {r_chk.status_code if r_chk else 'timeout'}")
#             if r_chk and r_chk.status_code == 200:
#                 dbg("stored ID confirmed valid ✔")
#             else:
#                 # ID is stale / wrong — clear it and search
#                 dbg("stored ID invalid — clearing and searching...")
#                 att_record_id = None

#         # ── Step 2: report search (if no valid ID yet) ─────────────────────
#         if not att_record_id:
#             att_record_id = _find_record_in_zoho(
#                 stored_worker, today_display, today_iso, hdrs, _log)
#             if att_record_id:
#                 lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                 save_lock(lock)

#         # ── Step 3: no-criteria probe — expose what the report actually has ─
#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             r_all = zoho_request("GET", report_url, headers=hdrs,
#                                  params={"from": 1, "limit": 5})
#             if r_all and r_all.status_code == 200:
#                 all_recs = r_all.json().get("data", [])
#                 dbg(f"no-criteria probe → {len(all_recs)} record(s) in report")
#                 for i, rec in enumerate(all_recs):
#                     dbg(f"  rec[{i}] keys={list(rec.keys())}")
#                     dbg(f"  rec[{i}] sample={ {k: rec[k] for k in list(rec.keys())[:8]} }")
#             else:
#                 status = r_all.status_code if r_all else "timeout"
#                 body   = r_all.text[:300] if r_all else "no response"
#                 dbg(f"no-criteria probe failed → HTTP {status}: {body}")

#             # ── Step 4: try the FORM endpoint directly (different from report) ─
#             # Zoho reports can have filters; the form index has everything.
#             form_index_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#             for date_val in (today_display, today_iso):
#                 crit = f'(Worker_Name == "{stored_worker}" && Date == "{date_val}")'
#                 r_f = zoho_request("GET", form_index_url, headers=hdrs,
#                                    params={"criteria": crit})
#                 dbg(f"form GET ({date_val}) → HTTP {r_f.status_code if r_f else 'timeout'}")
#                 if r_f and r_f.status_code == 200:
#                     frecs = r_f.json().get("data", [])
#                     dbg(f"  form returned {len(frecs)} record(s)")
#                     if frecs:
#                         att_record_id = frecs[0].get("ID")
#                         dbg(f"  ✔ found via form endpoint → ID={att_record_id}")
#                         lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                         save_lock(lock)
#                         break

#         if not att_record_id:
#             return False, (
#                 f"Could not locate today's attendance record in Zoho.\n"
#                 f"Worker: {full_name}  Date: {today_display}\n"
#                 f"Stored Zoho ID: {info.get('zoho_id', 'None')}\n"
#                 "Check the terminal/log for [checkout] diagnostics.\n"
#                 "The record may not have been created at check-in time."
#             )

#         # Hours calculation
#         # NOTE: Total_Hours rounded to 2 decimal places to stay within
#         # Zoho's field digit limit (e.g. 99.99 max).
#         try:
#             dt_in = datetime.strptime(info.get("time", ""), "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             dt_in = now
#         total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)
#         ot_hours    = overtime_hours(total_hours)
#         total_str   = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"
#         ot_str      = f"{int(ot_hours)}h {int((ot_hours % 1) * 60)}m" if ot_hours else "None"

#         # Round to 2dp — Zoho rejects values with too many decimal digits
#         total_hours_rounded = round(total_hours, 2)
#         ot_hours_rounded    = round(ot_hours, 2)
#         dbg(f"hours: total={total_hours_rounded}  overtime={ot_hours_rounded}")

#         # ── PATCH ──────────────────────────────────────────────────────────
#         # Daily_Attendance_Report is confirmed writable (returned HTTP 200).
#         update_url = (
#             f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#             f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
#         )
#         dbg(f"PATCH → {ATTENDANCE_REPORT}/{att_record_id}")
#         r_u = zoho_request("PATCH", update_url, headers=hdrs, json={"data": {
#             "Last_Out":       now.strftime("%d-%b-%Y %H:%M:%S"),
#             "Total_Hours":    total_hours_rounded,
#             "Overtime_Hours": ot_hours_rounded,
#         }})

#         http_code = r_u.status_code if r_u else "timeout"
#         body_raw  = r_u.text[:300] if r_u else "No response"
#         dbg(f"PATCH result → HTTP {http_code}  body={body_raw}")

#         if r_u and r_u.status_code == 200:
#             body = r_u.json()
#             code = body.get("code")
#             if code == 3000:
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = {
#                     "time":           now.strftime("%H:%M:%S"),
#                     "name":           full_name,
#                     "total_hours":    total_hours_rounded,
#                     "overtime_hours": ot_hours_rounded,
#                     "is_late":        info.get("is_late", False),
#                     "late_note":      info.get("late_note", ""),
#                     "checkin_time":   info.get("time", ""),
#                 }
#                 save_lock(lock)
#                 ot_line = f"   Overtime: {ot_str}" if ot_hours else ""
#                 return True, (
#                     f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}\n"
#                     f"   Total time: {total_str}\n"
#                     f"{ot_line}"
#                 )
#             # Field validation or other Zoho error — surface the full message
#             errors = body.get("error", body.get("message", ""))
#             return False, (
#                 f"Zoho rejected the update (code {code}).\n"
#                 f"Error: {errors}\n"
#                 f"Worker: {full_name}  Hours sent: {total_hours_rounded}"
#             )

#         return False, f"Check-out PATCH failed (HTTP {http_code}): {body_raw}"

#     return False, "Unknown action."

# # ===========================================================
# # DAILY SUMMARY EXPORT
# # ===========================================================
# def export_daily_summary():
#     """Write today's attendance to a CSV and return the filename."""
#     lock     = load_lock()
#     today    = lock.get("date", datetime.now().strftime("%Y-%m-%d"))
#     filename = f"attendance_{today}.csv"

#     rows = []
#     # Checked-out workers (complete records)
#     for zk_id, info in lock.get("checked_out", {}).items():
#         rows.append({
#             "ZK_ID":          zk_id,
#             "Name":           info.get("name", ""),
#             "Check-In":       info.get("checkin_time", ""),
#             "Check-Out":      info.get("time", ""),
#             "Total Hours":    info.get("total_hours", ""),
#             "Overtime Hours": info.get("overtime_hours", 0),
#             "Late?":          "Yes" if info.get("is_late") else "No",
#             "Late Note":      info.get("late_note", ""),
#             "Status":         "Complete",
#         })
#     # Still checked-in workers
#     for zk_id, info in lock.get("checked_in", {}).items():
#         rows.append({
#             "ZK_ID":          zk_id,
#             "Name":           info.get("name", ""),
#             "Check-In":       info.get("time", ""),
#             "Check-Out":      "—",
#             "Total Hours":    "—",
#             "Overtime Hours": "—",
#             "Late?":          "Yes" if info.get("is_late") else "No",
#             "Late Note":      info.get("late_note", ""),
#             "Status":         "Still In",
#         })

#     if not rows:
#         return None

#     fieldnames = ["ZK_ID","Name","Check-In","Check-Out",
#                   "Total Hours","Overtime Hours","Late?","Late Note","Status"]
#     with open(filename, "w", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(rows)
#     return filename

# # ===========================================================
# # COLOUR PALETTE  — Enterprise Command Center
# # ===========================================================
# BG         = "#07090f"
# CARD       = "#0c1018"
# CARD2      = "#10151f"
# CARD3      = "#141b27"
# BORDER     = "#1c2438"
# BORDER2    = "#243048"
# ACCENT     = "#3b82f6"
# ACCENT_DIM = "#172554"
# ACCENT2    = "#60a5fa"
# GREEN      = "#10b981"
# GREEN2     = "#34d399"
# GREEN_DIM  = "#052e1c"
# RED        = "#f43f5e"
# RED2       = "#fb7185"
# RED_DIM    = "#4c0519"
# ORANGE     = "#f59e0b"
# ORANGE2    = "#fbbf24"
# ORANGE_DIM = "#3d1f00"
# TEXT       = "#e2e8f0"
# TEXT2      = "#94a3b8"
# MUTED      = "#3d4f69"
# WHITE      = "#ffffff"
# GOLD       = "#f59e0b"
# GOLD2      = "#fde68a"
# PURPLE     = "#a78bfa"
# PURPLE_DIM = "#2e1065"


# # ===========================================================
# # SHARED UI HELPERS
# # ===========================================================
# def _btn_hover(btn, bg_on, fg_on, bg_off, fg_off):
#     """Attach hover enter/leave colour transitions to a Button."""
#     btn.bind("<Enter>", lambda _: btn.config(bg=bg_on, fg=fg_on))
#     btn.bind("<Leave>", lambda _: btn.config(bg=bg_off, fg=fg_off))

# def _make_sep(parent, color=BORDER, height=1):
#     tk.Frame(parent, bg=color, height=height).pack(fill=tk.X)

# def _initials(name):
#     """Return up to 2 initials from a full name."""
#     parts = name.strip().split()
#     if not parts:
#         return "??"
#     if len(parts) == 1:
#         return parts[0][:2].upper()
#     return (parts[0][0] + parts[-1][0]).upper()


# # ===========================================================
# # ADMIN PANEL
# # ===========================================================
# class AdminPanel(tk.Toplevel):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.title("Attendance Command Center")
#         self.configure(bg=BG)
#         self.resizable(True, True)
#         sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
#         W, H   = min(sw, 1100), min(sh, 680)
#         self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
#         self._build()
#         self.refresh()

#     def _build(self):
#         # ── Header ─────────────────────────────────────────
#         hdr = tk.Frame(self, bg=CARD)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=PURPLE, height=2).pack(fill=tk.X)
#         hi = tk.Frame(hdr, bg=CARD, padx=24, pady=14)
#         hi.pack(fill=tk.X)

#         lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="ATTENDANCE COMMAND CENTER",
#                  font=("Courier", 13, "bold"), bg=CARD, fg=PURPLE).pack(anchor="w")
#         self.sub_lbl = tk.Label(lf, text="", font=("Courier", 8), bg=CARD, fg=TEXT2)
#         self.sub_lbl.pack(anchor="w", pady=(2, 0))

#         rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
#         btn_refresh = tk.Button(rf, text="↻  REFRESH", font=("Courier", 9, "bold"),
#                                 relief=tk.FLAT, bg=ACCENT_DIM, fg=ACCENT2,
#                                 cursor="hand2", padx=14, pady=6, command=self.refresh)
#         btn_refresh.pack(side=tk.LEFT, padx=(0, 8))
#         _btn_hover(btn_refresh, ACCENT, WHITE, ACCENT_DIM, ACCENT2)

#         btn_exp = tk.Button(rf, text="⬇  EXPORT CSV", font=("Courier", 9, "bold"),
#                             relief=tk.FLAT, bg=GREEN_DIM, fg=GREEN2,
#                             cursor="hand2", padx=14, pady=6, command=self._export)
#         btn_exp.pack(side=tk.LEFT, padx=(0, 8))
#         _btn_hover(btn_exp, GREEN, BG, GREEN_DIM, GREEN2)

#         btn_close = tk.Button(rf, text="✕  CLOSE", font=("Courier", 9, "bold"),
#                               relief=tk.FLAT, bg=BORDER, fg=TEXT2,
#                               cursor="hand2", padx=14, pady=6, command=self.destroy)
#         btn_close.pack(side=tk.LEFT)
#         _btn_hover(btn_close, MUTED, WHITE, BORDER, TEXT2)

#         # ── KPI tiles ──────────────────────────────────────
#         self.kpi_fr = tk.Frame(self, bg=BG, padx=20, pady=12)
#         self.kpi_fr.pack(fill=tk.X)

#         # ── Table ──────────────────────────────────────────
#         _make_sep(self, BORDER2)
#         tree_wrap = tk.Frame(self, bg=BG, padx=20, pady=12)
#         tree_wrap.pack(fill=tk.BOTH, expand=True)

#         style = ttk.Style(self)
#         style.theme_use("default")
#         style.configure("Cmd.Treeview",
#                         background=CARD2, foreground=TEXT,
#                         fieldbackground=CARD2, rowheight=30,
#                         font=("Courier", 9), borderwidth=0)
#         style.configure("Cmd.Treeview.Heading",
#                         background=CARD, foreground=GOLD,
#                         font=("Courier", 9, "bold"),
#                         relief="flat", borderwidth=0)
#         style.map("Cmd.Treeview",
#                   background=[("selected", ACCENT_DIM)],
#                   foreground=[("selected", ACCENT2)])

#         cols    = ("Avatar", "Name", "Check-In", "Check-Out",
#                    "Hours", "Overtime", "Status", "Late")
#         widths  = (50, 200, 110, 110, 80, 90, 90, 80)
#         anchors = ("center","w","center","center","center","center","center","center")

#         self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings",
#                                   style="Cmd.Treeview", selectmode="browse")
#         for col, w, a in zip(cols, widths, anchors):
#             self.tree.heading(col, text=col.upper())
#             self.tree.column(col, width=w, anchor=a, stretch=(col == "Name"))

#         # Row colour tags
#         self.tree.tag_configure("late",     foreground=ORANGE2)
#         self.tree.tag_configure("ot",       foreground=PURPLE)
#         self.tree.tag_configure("complete", foreground=GREEN2)
#         self.tree.tag_configure("still_in", foreground=ACCENT2)
#         self.tree.tag_configure("alt",      background="#0e1320")

#         vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
#         self.tree.configure(yscrollcommand=vsb.set)
#         self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         vsb.pack(side=tk.RIGHT, fill=tk.Y)

#     # ── Refresh ────────────────────────────────────────────
#     def refresh(self):
#         for row in self.tree.get_children():
#             self.tree.delete(row)

#         lock        = load_lock()
#         checked_in  = lock.get("checked_in", {})
#         checked_out = lock.get("checked_out", {})
#         total       = len(checked_in) + len(checked_out)
#         late_count = ot_count = 0
#         now = datetime.now()
#         row_idx = 0

#         def _insert(values, tags):
#             nonlocal row_idx
#             if row_idx % 2 == 1:
#                 tags = list(tags) + ["alt"]
#             self.tree.insert("", tk.END, values=values, tags=tuple(tags))
#             row_idx += 1

#         # Completed workers
#         for zk_id, info in sorted(checked_out.items(),
#                                    key=lambda x: x[1].get("checkin_time", "")):
#             name  = info.get("name", zk_id)
#             ci    = info.get("checkin_time", "—")[-8:] if len(info.get("checkin_time",""))>8 else info.get("checkin_time","—")
#             co    = info.get("time", "—")
#             hrs   = info.get("total_hours", 0)
#             ot    = info.get("overtime_hours", 0)
#             late  = info.get("is_late", False)
#             h_str = f"{int(hrs)}h {int((hrs%1)*60):02d}m" if isinstance(hrs,(int,float)) else str(hrs)
#             o_str = f"{int(ot)}h {int((ot%1)*60):02d}m" if ot else "—"
#             if late:   late_count += 1
#             if ot > 0: ot_count   += 1
#             tags = []
#             if late:   tags.append("late")
#             if ot > 0: tags.append("ot")
#             tags.append("complete")
#             _insert((_initials(name), name, ci, co, h_str, o_str,
#                      "✔  COMPLETE", "⚠ LATE" if late else "—"), tags)

#         # Still-in workers
#         for zk_id, info in sorted(checked_in.items(),
#                                    key=lambda x: x[1].get("time", "")):
#             name = info.get("name", zk_id)
#             ci   = info.get("time", "—")
#             late = info.get("is_late", False)
#             try:
#                 dt_in    = datetime.strptime(ci, "%d-%b-%Y %H:%M:%S")
#                 elapsed  = (now - dt_in).total_seconds() / 3600
#                 h_str    = f"{int(elapsed)}h {int((elapsed%1)*60):02d}m"
#             except Exception:
#                 h_str = "—"
#             ci_short = ci[-8:] if len(ci) > 8 else ci
#             if late: late_count += 1
#             tags = ["late"] if late else []
#             tags.append("still_in")
#             _insert((_initials(name), name, ci_short, "—", h_str, "—",
#                      "● ACTIVE", "⚠ LATE" if late else "—"), tags)

#         # ── KPI tiles ──────────────────────────────────────
#         for w in self.kpi_fr.winfo_children():
#             w.destroy()

#         kpis = [
#             ("TOTAL TODAY",   total,              WHITE,   BORDER2),
#             ("CHECKED OUT",   len(checked_out),   GREEN2,  "#0a3321"),
#             ("ACTIVE / IN",   len(checked_in),    ACCENT2, "#0d1f3f"),
#             ("LATE ARRIVALS", late_count,          ORANGE2, "#3d1f00"),
#             ("OVERTIME",      ot_count,            PURPLE,  "#1e0a40"),
#         ]
#         for label, val, fg, border_col in kpis:
#             tile = tk.Frame(self.kpi_fr, bg=CARD2, padx=20, pady=10,
#                             highlightbackground=border_col, highlightthickness=1)
#             tile.pack(side=tk.LEFT, padx=(0, 10), fill=tk.Y)
#             tk.Label(tile, text=str(val), font=("Courier", 28, "bold"),
#                      bg=CARD2, fg=fg).pack()
#             tk.Label(tile, text=label, font=("Courier", 7, "bold"),
#                      bg=CARD2, fg=TEXT2).pack()

#         self.sub_lbl.config(
#             text=(f"Date: {lock.get('date','')}   "
#                   f"Shift: {SHIFT_START_H:02d}:{SHIFT_START_M:02d}   "
#                   f"Standard: {SHIFT_HOURS}h   "
#                   f"Grace: {GRACE_MINUTES} min   "
#                   f"Refreshed: {now.strftime('%H:%M:%S')}")
#         )

#     def _export(self):
#         fname = export_daily_summary()
#         if fname:
#             messagebox.showinfo("Export Complete",
#                                 f"Saved to:\n{os.path.abspath(fname)}", parent=self)
#         else:
#             messagebox.showwarning("Nothing to Export",
#                                    "No attendance records for today.", parent=self)


# # ===========================================================
# # FINGERPRINT SCAN ANIMATION  (Canvas ring)
# # ===========================================================
# class ScanRing(tk.Canvas):
#     """Animated concentric ring shown while waiting for a fingerprint."""
#     R    = 54
#     SIZE = 120

#     def __init__(self, parent):
#         super().__init__(parent, width=self.SIZE, height=self.SIZE,
#                          bg=CARD2, highlightthickness=0)
#         cx = cy = self.SIZE // 2
#         # Outer static ring
#         self.create_oval(cx-self.R, cy-self.R, cx+self.R, cy+self.R,
#                          outline=BORDER2, width=2)
#         # Inner pulsing arc
#         self._arc = self.create_arc(cx-self.R+6, cy-self.R+6,
#                                      cx+self.R-6, cy+self.R-6,
#                                      start=90, extent=0,
#                                      outline=ACCENT, width=3, style="arc")
#         # Centre dot
#         self._dot = self.create_oval(cx-6, cy-6, cx+6, cy+6,
#                                       fill=ACCENT, outline="")
#         self._angle = 0
#         self._active = False

#     def start(self):
#         self._active = True
#         self._animate()

#     def stop(self):
#         self._active = False
#         cx = cy = self.SIZE // 2
#         self.itemconfig(self._arc, extent=0)
#         self.itemconfig(self._dot, fill=GREEN)

#     def error(self):
#         self._active = False
#         self.itemconfig(self._dot, fill=RED)

#     def reset(self):
#         self._active = False
#         self.itemconfig(self._arc, extent=0)
#         self.itemconfig(self._dot, fill=ACCENT)

#     def _animate(self):
#         if not self._active:
#             return
#         self._angle = (self._angle + 8) % 360
#         # Arc sweeps 0→270→0 for a "breathing" effect
#         extent = int(270 * abs((self._angle % 180) - 90) / 90)
#         self.itemconfig(self._arc, start=self._angle, extent=extent)
#         self.after(30, self._animate)


# # ===========================================================
# # PULSING LED  (Canvas dot)
# # ===========================================================
# class PulseLED(tk.Canvas):
#     """A small animated status dot."""
#     SIZE = 12

#     def __init__(self, parent, color=ACCENT):
#         super().__init__(parent, width=self.SIZE, height=self.SIZE,
#                          bg=parent.cget("bg"), highlightthickness=0)
#         r = self.SIZE // 2
#         self._dot = self.create_oval(2, 2, r*2-2, r*2-2, fill=color, outline="")
#         self._color = color
#         self._phase = 0
#         self._pulse()

#     def set_color(self, color):
#         self._color = color
#         self.itemconfig(self._dot, fill=color)

#     def _pulse(self):
#         self._phase = (self._phase + 1) % 60
#         # Subtle brightness oscillation
#         alpha = 0.55 + 0.45 * abs((self._phase % 60) - 30) / 30
#         c = self._color
#         try:
#             r = int(int(c[1:3], 16) * alpha)
#             g = int(int(c[3:5], 16) * alpha)
#             b = int(int(c[5:7], 16) * alpha)
#             mixed = f"#{r:02x}{g:02x}{b:02x}"
#             self.itemconfig(self._dot, fill=mixed)
#         except Exception:
#             pass
#         self.after(50, self._pulse)


# # ===========================================================
# # MAIN GUI — Enterprise Edition
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Wavemark Properties — Attendance Terminal")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy         = False
#         self._debounce_job = None
#         self._worker_cache = {}
#         self._scan_active  = False

#         sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
#         W, H   = min(sw, 940), min(sh, 760)
#         self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

#         self._build_ui()
#         self._tick_clock()
#         self._tick_stats()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD ─────────────────────────────────────────────────
#     def _build_ui(self):
#         self._build_header()
#         self._build_body()
#         self._build_footer()
#         self._build_flash()

#     # ── HEADER ────────────────────────────────────────────────
#     def _build_header(self):
#         hdr = tk.Frame(self.root, bg=CARD)
#         hdr.pack(fill=tk.X)
#         # Gold accent stripe
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)

#         hi = tk.Frame(hdr, bg=CARD, padx=28, pady=14)
#         hi.pack(fill=tk.X)

#         # Left: branding
#         lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="WAVEMARK PROPERTIES LIMITED",
#                  font=("Courier", 11, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(lf, text="Biometric Attendance Terminal  ·  v3.0",
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(1, 0))

#         # Right: clock + admin
#         rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)

#         btn_admin = tk.Button(rf, text="⚙  ADMIN PANEL",
#                               font=("Courier", 8, "bold"), relief=tk.FLAT,
#                               bg=PURPLE_DIM, fg=PURPLE, activebackground=PURPLE,
#                               activeforeground=WHITE, cursor="hand2",
#                               padx=10, pady=5, command=self._open_admin)
#         btn_admin.pack(anchor="e", pady=(0, 6))
#         _btn_hover(btn_admin, PURPLE, WHITE, PURPLE_DIM, PURPLE)

#         self.date_lbl  = tk.Label(rf, text="", font=("Courier", 8),
#                                    bg=CARD, fg=TEXT2)
#         self.date_lbl.pack(anchor="e")
#         self.clock_lbl = tk.Label(rf, text="", font=("Courier", 24, "bold"),
#                                    bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")

#         # Shift info bar
#         _make_sep(self.root, BORDER2)
#         sbar = tk.Frame(self.root, bg=CARD2, padx=28, pady=6)
#         sbar.pack(fill=tk.X)
#         shift_txt = (f"SHIFT  {SHIFT_START_H:02d}:{SHIFT_START_M:02d}  ·  "
#                      f"STANDARD  {SHIFT_HOURS}H  ·  "
#                      f"GRACE PERIOD  {GRACE_MINUTES} MIN")
#         tk.Label(sbar, text=shift_txt, font=("Courier", 8),
#                  bg=CARD2, fg=MUTED).pack(side=tk.LEFT)

#         # Keyboard hint
#         tk.Label(sbar, text="ENTER → auto-action   ESC → clear",
#                  font=("Courier", 8), bg=CARD2, fg=MUTED).pack(side=tk.RIGHT)

#     # ── BODY ──────────────────────────────────────────────────
#     def _build_body(self):
#         body = tk.Frame(self.root, bg=BG, padx=30, pady=18)
#         body.pack(fill=tk.BOTH, expand=True)

#         # ── Two-column layout ───────────────────────────────
#         cols = tk.Frame(body, bg=BG)
#         cols.pack(fill=tk.BOTH, expand=True)

#         left  = tk.Frame(cols, bg=BG); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         vsep  = tk.Frame(cols, bg=BORDER, width=1); vsep.pack(side=tk.LEFT, fill=tk.Y, padx=18)
#         right = tk.Frame(cols, bg=BG, width=320); right.pack(side=tk.LEFT, fill=tk.Y)

#         self._build_left(left)
#         self._build_right(right)

#     def _build_left(self, parent):
#         # ── Worker ID input card ───────────────────────────
#         id_card = tk.Frame(parent, bg=CARD2,
#                             highlightbackground=BORDER2, highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 14))

#         # Card header row
#         ch = tk.Frame(id_card, bg=CARD, padx=18, pady=10)
#         ch.pack(fill=tk.X)
#         tk.Label(ch, text="WORKER IDENTIFICATION",
#                  font=("Courier", 8, "bold"), bg=CARD, fg=TEXT2).pack(side=tk.LEFT)
#         self._led = PulseLED(ch, MUTED)
#         self._led.pack(side=tk.RIGHT, padx=(0, 2))

#         _make_sep(id_card, BORDER)

#         ci = tk.Frame(id_card, bg=CARD2, padx=18, pady=16)
#         ci.pack(fill=tk.X)

#         # Entry row
#         er = tk.Frame(ci, bg=CARD2); er.pack(fill=tk.X)
#         tk.Label(er, text="ID", font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED, width=3, anchor="w").pack(side=tk.LEFT)

#         # Gold-bordered entry
#         eb = tk.Frame(er, bg=GOLD, padx=1, pady=1); eb.pack(side=tk.LEFT, padx=(6, 0))
#         ei = tk.Frame(eb, bg="#09101a"); ei.pack()
#         self.user_entry = tk.Entry(ei, font=("Courier", 28, "bold"), width=9,
#                                     bd=0, bg="#09101a", fg=WHITE,
#                                     insertbackground=GOLD, selectbackground=GOLD2,
#                                     selectforeground=BG)
#         self.user_entry.pack(padx=14, pady=8)
#         self.user_entry.bind("<KeyRelease>", self._on_key)
#         self.user_entry.bind("<Return>",     self._on_enter)
#         self.user_entry.bind("<Escape>",     lambda _: self._reset_ui())
#         self.user_entry.focus_set()

#         # Clear button
#         btn_clr = tk.Button(er, text="✕", font=("Courier", 10, "bold"),
#                             relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                             activebackground=RED_DIM, activeforeground=RED,
#                             cursor="hand2", padx=8, pady=4,
#                             command=self._reset_ui)
#         btn_clr.pack(side=tk.LEFT, padx=(10, 0))
#         _btn_hover(btn_clr, RED_DIM, RED, BORDER, MUTED)

#         # Identity display
#         idf = tk.Frame(ci, bg=CARD2); idf.pack(fill=tk.X, pady=(12, 0))

#         # Avatar circle (Canvas)
#         self._avatar_cv = tk.Canvas(idf, width=48, height=48,
#                                      bg=CARD2, highlightthickness=0)
#         self._avatar_cv.pack(side=tk.LEFT, padx=(0, 12))
#         self._avatar_circle = self._avatar_cv.create_oval(2, 2, 46, 46,
#                                                            fill=BORDER, outline="")
#         self._avatar_text   = self._avatar_cv.create_text(24, 24, text="",
#                                                             font=("Courier", 13, "bold"),
#                                                             fill=MUTED)

#         info_col = tk.Frame(idf, bg=CARD2); info_col.pack(side=tk.LEFT, fill=tk.X)
#         self.name_lbl = tk.Label(info_col, text="—",
#                                   font=("Courier", 16, "bold"), bg=CARD2, fg=MUTED)
#         self.name_lbl.pack(anchor="w")
#         self.hint_lbl = tk.Label(info_col, text="Enter a Worker ID above",
#                                   font=("Courier", 9), bg=CARD2, fg=MUTED)
#         self.hint_lbl.pack(anchor="w", pady=(2, 0))

#         # ── Status banner ──────────────────────────────────
#         self.sf = tk.Frame(parent, bg=ACCENT_DIM,
#                             highlightbackground=ACCENT, highlightthickness=1)
#         self.sf.pack(fill=tk.X, pady=(0, 14))
#         sb_inner = tk.Frame(self.sf, bg=ACCENT_DIM); sb_inner.pack(fill=tk.X, padx=16, pady=10)
#         self._status_led = PulseLED(sb_inner, ACCENT)
#         self._status_led.pack(side=tk.LEFT, padx=(0, 8))
#         self.sl = tk.Label(sb_inner, text="Awaiting Worker ID",
#                            font=("Courier", 10, "bold"), bg=ACCENT_DIM, fg=ACCENT,
#                            anchor="w")
#         self.sl.pack(side=tk.LEFT, fill=tk.X)

#         # ── Action buttons ─────────────────────────────────
#         br = tk.Frame(parent, bg=BG); br.pack(fill=tk.X, pady=(0, 14))

#         self.btn_in = tk.Button(br, text="▶   CHECK IN",
#                                 font=("Courier", 12, "bold"), width=16,
#                                 relief=tk.FLAT, bg=GREEN_DIM, fg=MUTED,
#                                 activebackground=GREEN, activeforeground=BG,
#                                 cursor="hand2", state=tk.DISABLED,
#                                 command=lambda: self._trigger("checkin"))
#         self.btn_in.pack(side=tk.LEFT, ipady=12, padx=(0, 10))

#         self.btn_out = tk.Button(br, text="◼   CHECK OUT",
#                                  font=("Courier", 12, "bold"), width=16,
#                                  relief=tk.FLAT, bg=RED_DIM, fg=MUTED,
#                                  activebackground=RED, activeforeground=WHITE,
#                                  cursor="hand2", state=tk.DISABLED,
#                                  command=lambda: self._trigger("checkout"))
#         self.btn_out.pack(side=tk.LEFT, ipady=12, padx=(0, 10))

#         btn_exp = tk.Button(br, text="⬇", font=("Courier", 11, "bold"),
#                             relief=tk.FLAT, bg=BORDER, fg=TEXT2,
#                             activebackground=GREEN_DIM, activeforeground=GREEN,
#                             cursor="hand2", padx=12, command=self._quick_export)
#         btn_exp.pack(side=tk.RIGHT, ipady=12)
#         _btn_hover(btn_exp, GREEN_DIM, GREEN2, BORDER, TEXT2)

#         # ── Divider ────────────────────────────────────────
#         _make_sep(parent, BORDER, height=1)
#         tk.Frame(parent, bg=BG, height=10).pack()

#         # ── Activity log ───────────────────────────────────
#         lh = tk.Frame(parent, bg=BG); lh.pack(fill=tk.X, pady=(0, 6))
#         tk.Label(lh, text="ACTIVITY LOG",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         btn_clrlog = tk.Button(lh, text="CLEAR", font=("Courier", 7, "bold"),
#                                relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                                padx=8, pady=2, cursor="hand2",
#                                command=self._clear_log)
#         btn_clrlog.pack(side=tk.RIGHT)
#         _btn_hover(btn_clrlog, BORDER2, TEXT2, BORDER, MUTED)

#         lw = tk.Frame(parent, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
#         lw.pack(fill=tk.BOTH, expand=True)
#         sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD)
#         sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(lw, font=("Courier", 9), bg=CARD, fg=TEXT2,
#                                relief=tk.FLAT, padx=14, pady=10,
#                                yscrollcommand=sb.set, state=tk.DISABLED,
#                                cursor="arrow")
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)

#         for tag, col in [("ok", GREEN2), ("err", RED2), ("warn", ORANGE2),
#                          ("info", ACCENT2), ("ts", MUTED), ("div", BORDER2),
#                          ("late", ORANGE), ("ot", PURPLE)]:
#             self.log_box.tag_config(tag, foreground=col)

#     def _build_right(self, parent):
#         """Right panel: scan ring + today's mini stats."""
#         tk.Label(parent, text="BIOMETRIC SCANNER",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 10))

#         # Scanner card
#         sc = tk.Frame(parent, bg=CARD2,
#                        highlightbackground=BORDER2, highlightthickness=1)
#         sc.pack(fill=tk.X, pady=(0, 16))
#         sc_inner = tk.Frame(sc, bg=CARD2, pady=20)
#         sc_inner.pack()

#         self._ring = ScanRing(sc_inner)
#         self._ring.pack(pady=(0, 10))

#         self._scan_lbl = tk.Label(sc_inner, text="READY",
#                                    font=("Courier", 9, "bold"), bg=CARD2, fg=MUTED)
#         self._scan_lbl.pack()
#         self._scan_sub = tk.Label(sc_inner, text="Place finger when prompted",
#                                    font=("Courier", 7), bg=CARD2, fg=MUTED, wraplength=200)
#         self._scan_sub.pack(pady=(2, 0))

#         # ── Today's stats card ──────────────────────────────
#         tk.Label(parent, text="TODAY'S SUMMARY",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 8))

#         self._stats_fr = tk.Frame(parent, bg=BG)
#         self._stats_fr.pack(fill=tk.X)

#         # Will be populated by _tick_stats
#         self._stat_tiles = {}
#         stat_defs = [
#             ("checked_out", "COMPLETED",  GREEN2,  "#0a3321"),
#             ("checked_in",  "ON-SITE",    ACCENT2, "#0d1f3f"),
#             ("late",        "LATE",       ORANGE2, "#3d1f00"),
#             ("overtime",    "OVERTIME",   PURPLE,  "#1e0a40"),
#         ]
#         for i, (key, label, fg, bg2) in enumerate(stat_defs):
#             tile = tk.Frame(self._stats_fr, bg=CARD2, padx=12, pady=8,
#                             highlightbackground=bg2, highlightthickness=1)
#             r, c = divmod(i, 2)
#             tile.grid(row=r, column=c, padx=(0,8) if c==0 else 0,
#                       pady=(0,8) if r==0 else 0, sticky="ew")
#             self._stats_fr.columnconfigure(c, weight=1)
#             val_lbl = tk.Label(tile, text="0", font=("Courier", 22, "bold"),
#                                bg=CARD2, fg=fg)
#             val_lbl.pack()
#             tk.Label(tile, text=label, font=("Courier", 7, "bold"),
#                      bg=CARD2, fg=TEXT2).pack()
#             self._stat_tiles[key] = val_lbl

#         # ── Recent events mini-log ──────────────────────────
#         tk.Label(parent, text="RECENT EVENTS",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w",
#                                                                       pady=(14, 6))
#         ev_fr = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
#         ev_fr.pack(fill=tk.BOTH, expand=True)
#         self._event_box = tk.Text(ev_fr, font=("Courier", 8), bg=CARD, fg=TEXT2,
#                                    relief=tk.FLAT, padx=10, pady=8,
#                                    state=tk.DISABLED, cursor="arrow", height=8)
#         self._event_box.pack(fill=tk.BOTH, expand=True)
#         for tag, col in [("in", GREEN2), ("out", ACCENT2), ("warn", ORANGE2),
#                          ("ts", MUTED)]:
#             self._event_box.tag_config(tag, foreground=col)

#     # ── FOOTER (live stats bar) ────────────────────────────
#     def _build_footer(self):
#         _make_sep(self.root, BORDER2)
#         foot = tk.Frame(self.root, bg=CARD, padx=28, pady=7)
#         foot.pack(fill=tk.X, side=tk.BOTTOM)
#         self._foot_lbl = tk.Label(foot, text="", font=("Courier", 8),
#                                    bg=CARD, fg=MUTED)
#         self._foot_lbl.pack(side=tk.LEFT)
#         tk.Label(foot, text=f"Shift {SHIFT_START_H:02d}:{SHIFT_START_M:02d} – "
#                              f"{(SHIFT_START_H+SHIFT_HOURS)%24:02d}:{SHIFT_START_M:02d}  "
#                              f"·  {SHIFT_HOURS}h standard  ·  {GRACE_MINUTES}min grace",
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(side=tk.RIGHT)

#     # ── FLASH OVERLAY ─────────────────────────────────────
#     def _build_flash(self):
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.fi = tk.Label(self.flash, font=("Courier", 60, "bold"), bg=ACCENT, fg=WHITE)
#         self.fi.place(relx=0.5, rely=0.28, anchor="center")
#         self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
#                            bg=ACCENT, fg=WHITE, wraplength=740)
#         self.fm.place(relx=0.5, rely=0.45, anchor="center")
#         self.fs = tk.Label(self.flash, font=("Courier", 12),
#                            bg=ACCENT, fg="#c7d9ff", wraplength=740)
#         self.fs.place(relx=0.5, rely=0.56, anchor="center")
#         self.fx = tk.Label(self.flash, font=("Courier", 11, "bold"),
#                            bg=ACCENT, fg=GOLD2, wraplength=740)
#         self.fx.place(relx=0.5, rely=0.65, anchor="center")

#     # ── CLOCK ─────────────────────────────────────────────
#     def _tick_clock(self):
#         n = datetime.now()
#         self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
#         self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── LIVE STATS ────────────────────────────────────────
#     def _tick_stats(self):
#         lock = load_lock()
#         cin  = lock.get("checked_in",  {})
#         cout = lock.get("checked_out", {})
#         late = sum(1 for v in {**cin, **cout}.values()
#                    if isinstance(v, dict) and v.get("is_late"))
#         ot   = sum(1 for v in cout.values()
#                    if isinstance(v, dict) and v.get("overtime_hours", 0) > 0)
#         self._stat_tiles["checked_out"].config(text=str(len(cout)))
#         self._stat_tiles["checked_in"].config(text=str(len(cin)))
#         self._stat_tiles["late"].config(text=str(late))
#         self._stat_tiles["overtime"].config(text=str(ot))
#         total = len(cin) + len(cout)
#         self._foot_lbl.config(
#             text=f"Workers today: {total}   "
#                  f"On-site: {len(cin)}   "
#                  f"Completed: {len(cout)}   "
#                  f"Late: {late}   Overtime: {ot}")
#         self.root.after(8000, self._tick_stats)

#     # ── ADMIN ─────────────────────────────────────────────
#     def _open_admin(self):
#         AdminPanel(self.root)

#     # ── EXPORT ────────────────────────────────────────────
#     def _quick_export(self):
#         fname = export_daily_summary()
#         if fname:
#             self.log(f"Exported → {os.path.abspath(fname)}", "ok")
#             self._add_event("Export", fname, "ts")
#         else:
#             self.log("Nothing to export — no records today.", "warn")

#     # ── LOGGING ───────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END,
#                                 f"[{datetime.now().strftime('%H:%M:%S')}] ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     def _add_event(self, action, name, tag="ts"):
#         """Add a line to the right-panel recent events box."""
#         def _do():
#             self._event_box.config(state=tk.NORMAL)
#             ts = datetime.now().strftime("%H:%M")
#             self._event_box.insert("1.0",
#                                    f"{ts}  {action:<8}  {name}\n", tag)
#             self._event_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     # ── FLASH ─────────────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, extra, color):
#         self.flash.config(bg=color)
#         for w, v in [(self.fi, icon), (self.fm, headline),
#                      (self.fs, sub), (self.fx, extra)]:
#             w.config(text=v, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2400, self.flash.place_forget)

#     # ── SCANNER UI ────────────────────────────────────────
#     def _scan_start(self):
#         self._ring.start()
#         self._scan_lbl.config(text="SCANNING...", fg=ORANGE2)
#         self._scan_sub.config(text="Place your finger on the reader now")

#     def _scan_ok(self):
#         self._ring.stop()
#         self._scan_lbl.config(text="CAPTURED ✔", fg=GREEN2)
#         self._scan_sub.config(text="Processing...")

#     def _scan_err(self, msg="FAILED"):
#         self._ring.error()
#         self._scan_lbl.config(text=msg, fg=RED2)
#         self._scan_sub.config(text="Please try again")

#     def _scan_reset(self):
#         self._ring.reset()
#         self._scan_lbl.config(text="READY", fg=MUTED)
#         self._scan_sub.config(text="Place finger when prompted")

#     # ── STATUS & BUTTONS ──────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.sf.config(bg=bg, highlightbackground=border)
#             for w in self.sf.winfo_children():
#                 inner = w.winfo_children()
#                 for iw in ([w] + list(inner)):
#                     try: iw.config(bg=bg)
#                     except Exception: pass
#             self.sl.config(text=text, fg=fg, bg=bg)
#             self._status_led.config(bg=bg)
#             self._status_led.set_color(fg)
#             self._led.set_color(fg)
#         self.root.after(0, _do)

#     def _set_buttons(self, in_s, out_s):
#         def _do():
#             self.btn_in.config(
#                 state=in_s,
#                 bg=GREEN    if in_s == tk.NORMAL else GREEN_DIM,
#                 fg=BG       if in_s == tk.NORMAL else MUTED)
#             self.btn_out.config(
#                 state=out_s,
#                 bg=RED      if out_s == tk.NORMAL else RED_DIM,
#                 fg=WHITE    if out_s == tk.NORMAL else MUTED)
#             if in_s == tk.NORMAL:
#                 _btn_hover(self.btn_in,  GREEN2, BG,    GREEN,    BG)
#             if out_s == tk.NORMAL:
#                 _btn_hover(self.btn_out, RED2,   WHITE, RED,      WHITE)
#         self.root.after(0, _do)

#     def _set_avatar(self, name=None, color=BORDER):
#         initials = _initials(name) if name else ""
#         self._avatar_cv.itemconfig(self._avatar_circle, fill=color)
#         self._avatar_cv.itemconfig(self._avatar_text, text=initials,
#                                     fill=WHITE if name else MUTED)

#     def _apply_status(self, status, name=None):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Attendance complete — see you tomorrow",
#                              RED, RED_DIM, RED)
#             self._set_avatar(name, RED_DIM)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status("Already checked IN — proceed to Check-Out",
#                              ORANGE, ORANGE_DIM, ORANGE)
#             self._set_avatar(name, ORANGE_DIM)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status("Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
#             self._set_avatar(name, GREEN_DIM)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
#             self._set_avatar(None, BORDER)

#     # ── ID VALIDATION ─────────────────────────────────────
#     def _on_key(self, _=None):
#         if self._debounce_job:
#             self.root.after_cancel(self._debounce_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._soft_reset(); return
#         self._apply_status(get_worker_status(uid))
#         self._debounce_job = self.root.after(
#             650, lambda: threading.Thread(
#                 target=self._validate, args=(uid,), daemon=True).start())

#     def _validate(self, uid):
#         if self.user_entry.get().strip() != uid or self._busy:
#             return
#         worker = self._worker_cache.get(uid) or find_worker(uid)
#         if worker:
#             self._worker_cache[uid] = worker
#         if self.user_entry.get().strip() != uid:
#             return

#         def _upd():
#             if not worker:
#                 self.name_lbl.config(text="Unknown ID", fg=RED2)
#                 self.hint_lbl.config(text=f"ID '{uid}' not found — contact admin", fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(f"Worker ID {uid} does not exist", RED, RED_DIM, RED)
#                 self._set_avatar(None, RED_DIM)
#             else:
#                 name   = worker.get("Full_Name", "N/A")
#                 status = get_worker_status(uid)
#                 self.name_lbl.config(text=name, fg=WHITE)
#                 hints = {
#                     "checked_in": (f"Checked in today — use Check-Out", ORANGE),
#                     "done":       ("Attendance complete for today",       RED),
#                     "none":       ("Not yet checked in today",            TEXT2),
#                 }
#                 htxt, hcol = hints.get(status, ("", TEXT2))
#                 self.hint_lbl.config(text=htxt, fg=hcol)
#                 self._apply_status(status, name)
#         self.root.after(0, _upd)

#     def _on_enter(self, _=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy: return
#         s = get_worker_status(uid)
#         if s == "none":         self._trigger("checkin")
#         elif s == "checked_in": self._trigger("checkout")

#     # ── TRIGGER ───────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy: return
#         uid = self.user_entry.get().strip()
#         if not uid: return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         verb = "CHECK IN" if action == "checkin" else "CHECK OUT"
#         self._set_status(f"Scanning fingerprint for {verb}…",
#                          ORANGE, ORANGE_DIM, ORANGE)
#         self.root.after(0, self._scan_start)
#         threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

#     # ── MAIN WORKER THREAD ────────────────────────────────
#     def _process(self, uid, action):
#         is_open   = False
#         success   = False
#         msg       = ""
#         full_name = uid
#         try:
#             self.log(f"{'─'*18} {action.upper()} · ID {uid} {'─'*18}", "div")

#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._scan_err("NO DEVICE"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Connect the fingerprint device and try again.", "", "#6d28d9"))
#                 return

#             zk.OpenDevice(0); is_open = True
#             self.log("Waiting for fingerprint…", "info")
#             capture = None
#             for _ in range(150):
#                 capture = zk.AcquireFingerprint()
#                 if capture: break
#                 time.sleep(0.2)

#             if not capture:
#                 self.log("Scan timed out", "err")
#                 self.root.after(0, lambda: self._scan_err("TIMEOUT"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout", "No fingerprint detected.", "", "#92400e"))
#                 return

#             self.root.after(0, self._scan_ok)
#             self.log("Fingerprint captured ✔", "ok")

#             worker = self._worker_cache.get(uid) or find_worker(uid)
#             if worker: self._worker_cache[uid] = worker
#             if not worker:
#                 self.log(f"ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._scan_err("NOT FOUND"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found",
#                     f"ID {uid} does not exist in the system.", "", RED_DIM))
#                 return

#             full_name = worker.get("Full_Name", uid)
#             self.log(f"Identity: {full_name}", "ok")

#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log("Attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Complete", full_name,
#                     "Attendance is done for today.", "#1e0a40"))
#                 self.root.after(2600, lambda: self._apply_status("done", full_name))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log("Already checked IN — redirecting to Check-Out", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In",
#                     f"{full_name}", "Please use Check-Out instead.", "#3d1f00"))
#                 self.root.after(2600, lambda: self._apply_status("checked_in", full_name))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log("Not checked IN yet", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In",
#                     f"{full_name}", "You must check IN before checking out.", "#1e0a40"))
#                 self.root.after(2600, lambda: self._apply_status("none", full_name))
#                 return

#             self.log(f"Posting {action.upper()} to Zoho…", "info")
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID
#             success, msg = log_attendance(worker["ID"], uid, pid, full_name, action, self.log)

#             tag = "ok" if success else "err"
#             for line in msg.splitlines():
#                 if line.strip():
#                     ltag = tag
#                     if "late"     in line.lower(): ltag = "late"
#                     if "overtime" in line.lower(): ltag = "ot"
#                     self.log(line.strip(), ltag)

#             if success:
#                 verb  = "Checked IN" if action == "checkin" else "Checked OUT"
#                 sub   = datetime.now().strftime("Time: %H:%M:%S · %A, %d %B %Y")
#                 extra = ""
#                 if action == "checkin" and is_late(datetime.now()):
#                     extra = f"⚠  Late arrival — {late_by_str(datetime.now())}"
#                 if action == "checkout":
#                     lock2 = load_lock()
#                     co    = lock2.get("checked_out", {}).get(str(uid), {})
#                     ot    = co.get("overtime_hours", 0) if isinstance(co, dict) else 0
#                     if ot > 0:
#                         extra = f"⏱  Overtime: {int(ot)}h {int((ot%1)*60)}m"

#                 flash_col = "#1d4ed8"
#                 if action == "checkin" and is_late(datetime.now()):
#                     flash_col = "#92400e"

#                 ev_tag = "in" if action == "checkin" else "out"
#                 self._add_event(verb, full_name, ev_tag)
#                 self._tick_stats()

#                 _v, _s, _e, _fc = verb, sub, extra, flash_col
#                 self.root.after(0, lambda: self._show_flash(
#                     "✔", f"{_v} — {full_name}", _s, _e, _fc))
#             else:
#                 _m = msg.splitlines()[0][:80]
#                 self.root.after(0, lambda: self._scan_err("ERROR"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", _m, "", RED_DIM))

#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")
#         finally:
#             if is_open:
#                 try: zk.CloseDevice()
#                 except: pass
#             self._busy = False
#             self.root.after(2600, lambda: self._scan_reset())
#             self.root.after(2600, lambda: self._reset_ui(clear_log=success))

#     # ── RESET ─────────────────────────────────────────────
#     def _reset_ui(self, clear_log=False):
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="—", fg=MUTED)
#         self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
#         self._set_avatar(None, BORDER)
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
#         if clear_log:
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.delete("1.0", tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.log("Ready for next worker.", "div")
#         self.user_entry.focus_set()

#     def _soft_reset(self):
#         self.name_lbl.config(text="—", fg=MUTED)
#         self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
#         self._set_avatar(None, BORDER)
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ─────────────────────────────────────────────
#     def _on_close(self):
#         try: zk.Terminate()
#         except: pass
#         self.root.destroy()


# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop







# import os, time, json, csv, requests, threading, math
# from datetime import datetime, timedelta
# from dotenv import load_dotenv
# from pyzkfp import ZKFP2
# import tkinter as tk
# from tkinter import ttk, messagebox

# # ===========================================================
# # CONFIGURATION
# # ===========================================================
# load_dotenv()
# ZOHO_DOMAIN      = os.getenv("ZOHO_DOMAIN", "zoho.com")
# APP_OWNER        = "wavemarkpropertieslimited"
# APP_NAME         = "real-estate-wages-system"
# CLIENT_ID        = os.getenv("ZOHO_CLIENT_ID")
# CLIENT_SECRET    = os.getenv("ZOHO_CLIENT_SECRET")
# REFRESH_TOKEN    = os.getenv("ZOHO_REFRESH_TOKEN")
# WORKERS_REPORT   = "All_Workers"
# ATTENDANCE_FORM  = "Daily_Attendance"
# ATTENDANCE_REPORT= "Daily_Attendance_Report"
# DEFAULT_PROJECT_ID = "4838902000000391493"
# TOKEN_CACHE      = {"token": None, "expires_at": 0}
# API_DOMAIN       = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
# CHECKIN_LOCK_FILE= "checkin_today.json"

# # ── Shift policy ──────────────────────────────────────────
# SHIFT_START_H    = 7     # 07:00 AM
# SHIFT_START_M    = 0
# SHIFT_HOURS      = 8     # standard hours before overtime kicks in
# GRACE_MINUTES    = 10    # 10-min grace period before "late" is flagged
# EARLY_CHECKOUT_H = 17    # 5:00 PM — checkout before this = early
# EARLY_CHECKOUT_M = 0

# # ===========================================================
# # GLOBAL SDK
# # ===========================================================
# zk = ZKFP2()
# try:
#     zk.Init()
# except Exception as e:
#     print(f"Fingerprint SDK Init Error: {e}")

# # ===========================================================
# # NETWORK & AUTHENTICATION
# # ===========================================================
# def zoho_request(method, url, retries=3, **kwargs):
#     kwargs.setdefault("timeout", 45)
#     for attempt in range(1, retries + 1):
#         try:
#             return requests.request(method, url, **kwargs)
#         except (requests.exceptions.Timeout,
#                 requests.exceptions.ConnectionError, OSError):
#             if attempt < retries:
#                 time.sleep(2 * attempt)
#     return None

# def get_access_token():
#     now = time.time()
#     if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
#         return TOKEN_CACHE["token"]
#     TOKEN_CACHE["token"] = None
#     url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
#     data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
#     for _ in range(3):
#         r = zoho_request("POST", url, data=data, retries=1)
#         if r and r.status_code == 200:
#             res = r.json()
#             TOKEN_CACHE["token"]      = res.get("access_token")
#             TOKEN_CACHE["expires_at"] = now + int(res.get("expires_in", 3600))
#             return TOKEN_CACHE["token"]
#         time.sleep(3)
#     return None

# def auth_headers():
#     token = get_access_token()
#     return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# # ===========================================================
# # LOCAL STATE
# # ===========================================================
# def load_lock():
#     today = datetime.now().strftime("%Y-%m-%d")
#     if os.path.exists(CHECKIN_LOCK_FILE):
#         try:
#             with open(CHECKIN_LOCK_FILE, "r") as f:
#                 data = json.load(f)
#             if data.get("date") == today:
#                 return data
#         except Exception:
#             pass
#     fresh = {"date": today, "checked_in": {}, "checked_out": {}}
#     save_lock(fresh)
#     return fresh

# def save_lock(data):
#     tmp = CHECKIN_LOCK_FILE + ".tmp"
#     with open(tmp, "w") as f:
#         json.dump(data, f, indent=2)
#     os.replace(tmp, CHECKIN_LOCK_FILE)

# def get_worker_status(zk_id):
#     lock = load_lock()
#     key  = str(zk_id)
#     if key in lock["checked_out"]:  return "done"
#     if key in lock["checked_in"]:   return "checked_in"
#     return "none"

# def count_early_checkouts(lock=None):
#     """Count workers who checked out before EARLY_CHECKOUT_H:EARLY_CHECKOUT_M."""
#     if lock is None:
#         lock = load_lock()
#     now = datetime.now()
#     early_limit = now.replace(
#         hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
#         second=0, microsecond=0)
#     count = 0
#     for info in lock.get("checked_out", {}).values():
#         if not isinstance(info, dict):
#             continue
#         co_time_str = info.get("time", "")
#         try:
#             co_dt = datetime.strptime(co_time_str, "%H:%M:%S").replace(
#                 year=now.year, month=now.month, day=now.day)
#             if co_dt < early_limit:
#                 count += 1
#         except Exception:
#             pass
#     return count

# # ===========================================================
# # SHIFT HELPERS
# # ===========================================================
# def is_late(checkin_dt):
#     cutoff = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M,
#         second=0, microsecond=0) + timedelta(minutes=GRACE_MINUTES)
#     return checkin_dt > cutoff

# def late_by_str(checkin_dt):
#     shift_start = checkin_dt.replace(
#         hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0)
#     delta = max((checkin_dt - shift_start).total_seconds(), 0)
#     mins  = int(delta // 60)
#     return f"{mins} min late" if mins else "on time"

# def overtime_hours(total_hours):
#     return max(round(total_hours - SHIFT_HOURS, 4), 0)

# # ===========================================================
# # ZOHO API
# # ===========================================================
# def find_worker(zk_user_id):
#     url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
#     criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
#     r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
#     if r and r.status_code == 200:
#         data = r.json().get("data", [])
#         return data[0] if data else None
#     return None

# def _extract_zoho_id(res_json):
#     data = res_json.get("data")
#     if isinstance(data, dict):
#         return data.get("ID") or data.get("id")
#     if isinstance(data, list) and data:
#         return data[0].get("ID") or data[0].get("id")
#     return res_json.get("ID") or res_json.get("id")

# def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs, _log=None):
#     def dbg(msg):
#         print(f"[ZOHO SEARCH] {msg}")
#         if _log: _log(f"[search] {msg}", "warn")
#     report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#     dbg(f"worker_id={worker_id} dates={today_display}/{today_iso}")
#     criteria_list = [
#         f'(Worker_Name == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_Name == "{worker_id}" && Date == "{today_iso}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
#         f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
#         f'(Worker_Name == "{worker_id}")',
#         f'(Worker_ID_Lookup == "{worker_id}")',
#     ]
#     for crit in criteria_list:
#         r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
#         if not r or r.status_code != 200:
#             dbg(f"  HTTP {r.status_code if r else 'timeout'} → {crit}"); continue
#         recs = r.json().get("data", [])
#         dbg(f"  {len(recs)} result(s) → {crit}")
#         if not recs: continue
#         for rec in recs:
#             d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
#             if d in (today_display, today_iso):
#                 dbg(f"  ✔ date-matched record ID={rec['ID']}"); return rec["ID"]
#         if len(recs) == 1:
#             dbg(f"  ✔ single-result fallback ID={recs[0]['ID']}"); return recs[0]["ID"]
#     dbg("  Trying date-only broad search...")
#     for date_val in (today_display, today_iso):
#         r = zoho_request("GET", report_url, headers=hdrs,
#                          params={"criteria": f'(Date == "{date_val}")'})
#         if not r or r.status_code != 200: continue
#         recs = r.json().get("data", [])
#         dbg(f"  date-only → {len(recs)} record(s) for {date_val}")
#         for rec in recs:
#             for field in ("Worker_Name","Worker_ID_Lookup","Worker","Worker_Name.ID","Worker_ID"):
#                 val = rec.get(field)
#                 if isinstance(val, dict):
#                     val = (val.get("ID") or val.get("id") or val.get("display_value",""))
#                 if str(val).strip() == str(worker_id).strip():
#                     dbg(f"  ✔ client-matched via '{field}' → ID={rec['ID']}"); return rec["ID"]
#         if recs:
#             dbg(f"  First record keys: {list(recs[0].keys())}")
#             dbg(f"  First record sample: { {k: recs[0][k] for k in list(recs[0].keys())[:10]} }")
#     dbg("  ✗ All strategies exhausted — record not found.")
#     return None

# # ===========================================================
# # ATTENDANCE LOGIC
# # ===========================================================
# def log_attendance(worker_id, zk_id, project_id, full_name, action, _log=None):
#     now       = datetime.now()
#     zk_key    = str(zk_id)
#     today_display = now.strftime("%d-%b-%Y")
#     today_iso     = now.strftime("%Y-%m-%d")

#     if action == "checkin":
#         form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
#         hdrs         = auth_headers()
#         worker_late  = is_late(now)
#         late_note    = late_by_str(now)
#         payload = {"data": {
#             "Worker_Name": worker_id, "Projects": project_id,
#             "Date": today_display, "First_In": checkin_time,
#             "Worker_Full_Name": full_name,
#             "Is_Late": "true" if worker_late else "false",
#             "Late_By_Minutes": int(max((now - now.replace(
#                 hour=SHIFT_START_H, minute=SHIFT_START_M,
#                 second=0, microsecond=0)).total_seconds() // 60, 0)) if worker_late else 0,
#         }}
#         r = zoho_request("POST", form_url, headers=hdrs, json=payload)
#         if r and r.status_code in (200, 201):
#             res          = r.json()
#             zoho_rec_id  = _extract_zoho_id(res)
#             if not zoho_rec_id:
#                 zoho_rec_id = _find_record_in_zoho(
#                     worker_id, today_display, today_iso, auth_headers(), _log)
#             lock = load_lock()
#             lock["checked_in"][zk_key] = {
#                 "time": checkin_time, "zoho_id": zoho_rec_id,
#                 "worker_id": worker_id, "name": full_name,
#                 "is_late": worker_late, "late_note": late_note,
#             }
#             save_lock(lock)
#             status_line = f"⚠ {late_note}" if worker_late else "✓ On time"
#             return True, (
#                 f"✅ {full_name} checked IN at {now.strftime('%H:%M')}\n"
#                 f"   {status_line}")
#         err = r.text[:200] if r else "Timeout"
#         return False, f"Check-in failed: {err}"

#     elif action == "checkout":
#         lock = load_lock()
#         info = lock["checked_in"].get(zk_key)
#         if not info:
#             return False, "No check-in record found for today."
#         hdrs = auth_headers()
#         if not hdrs:
#             return False, "Could not refresh Zoho token — check internet."
#         att_record_id  = info.get("zoho_id")
#         stored_worker  = info.get("worker_id", worker_id)

#         def dbg(msg):
#             print(f"[CHECKOUT] {msg}")
#             if _log: _log(f"[checkout] {msg}", "warn")

#         dbg(f"stored zoho_id={att_record_id} stored_worker={stored_worker}")

#         if att_record_id:
#             direct_url = (f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#                           f"/report/{ATTENDANCE_REPORT}/{att_record_id}")
#             r_chk = zoho_request("GET", direct_url, headers=hdrs)
#             dbg(f"direct GET by ID → HTTP {r_chk.status_code if r_chk else 'timeout'}")
#             if r_chk and r_chk.status_code == 200:
#                 dbg("stored ID confirmed valid ✔")
#             else:
#                 dbg("stored ID invalid — clearing and searching...")
#                 att_record_id = None

#         if not att_record_id:
#             att_record_id = _find_record_in_zoho(
#                 stored_worker, today_display, today_iso, hdrs, _log)
#             if att_record_id:
#                 lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                 save_lock(lock)

#         if not att_record_id:
#             report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
#             r_all = zoho_request("GET", report_url, headers=hdrs,
#                                  params={"from": 1, "limit": 5})
#             if r_all and r_all.status_code == 200:
#                 all_recs = r_all.json().get("data", [])
#                 dbg(f"no-criteria probe → {len(all_recs)} record(s) in report")
#                 for i, rec in enumerate(all_recs):
#                     dbg(f"  rec[{i}] keys={list(rec.keys())}")
#                     dbg(f"  rec[{i}] sample={ {k: rec[k] for k in list(rec.keys())[:8]} }")

#         form_index_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
#         for date_val in (today_display, today_iso):
#             crit = f'(Worker_Name == "{stored_worker}" && Date == "{date_val}")'
#             r_f  = zoho_request("GET", form_index_url, headers=hdrs, params={"criteria": crit})
#             dbg(f"form GET ({date_val}) → HTTP {r_f.status_code if r_f else 'timeout'}")
#             if r_f and r_f.status_code == 200:
#                 frecs = r_f.json().get("data", [])
#                 dbg(f"  form returned {len(frecs)} record(s)")
#                 if frecs:
#                     att_record_id = frecs[0].get("ID")
#                     dbg(f"  ✔ found via form endpoint → ID={att_record_id}")
#                     lock["checked_in"][zk_key]["zoho_id"] = att_record_id
#                     save_lock(lock)
#                     break

#         if not att_record_id:
#             return False, (
#                 f"Could not locate today's attendance record in Zoho.\n"
#                 f"Worker: {full_name} Date: {today_display}\n"
#                 f"Stored Zoho ID: {info.get('zoho_id', 'None')}\n"
#                 "Check the terminal/log for [checkout] diagnostics.\n"
#                 "The record may not have been created at check-in time.")

#         try:
#             dt_in = datetime.strptime(info.get("time", ""), "%d-%b-%Y %H:%M:%S")
#         except Exception:
#             dt_in = now
#         total_hours       = max((now - dt_in).total_seconds() / 3600, 0.01)
#         ot_hours          = overtime_hours(total_hours)
#         total_str         = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"
#         ot_str            = f"{int(ot_hours)}h {int((ot_hours % 1) * 60)}m" if ot_hours else "None"
#         total_hours_rounded = round(total_hours, 2)
#         ot_hours_rounded    = round(ot_hours, 2)
#         dbg(f"hours: total={total_hours_rounded} overtime={ot_hours_rounded}")

#         update_url = (f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
#                       f"/report/{ATTENDANCE_REPORT}/{att_record_id}")
#         dbg(f"PATCH → {ATTENDANCE_REPORT}/{att_record_id}")
#         r_u = zoho_request("PATCH", update_url, headers=hdrs, json={"data": {
#             "Last_Out": now.strftime("%d-%b-%Y %H:%M:%S"),
#             "Total_Hours": total_hours_rounded,
#             "Overtime_Hours": ot_hours_rounded,
#         }})
#         http_code = r_u.status_code if r_u else "timeout"
#         body_raw  = r_u.text[:300] if r_u else "No response"
#         dbg(f"PATCH result → HTTP {http_code} body={body_raw}")

#         if r_u and r_u.status_code == 200:
#             body = r_u.json()
#             code = body.get("code")
#             if code == 3000:
#                 checkout_time_str = now.strftime("%H:%M:%S")
#                 lock["checked_in"].pop(zk_key, None)
#                 lock["checked_out"][zk_key] = {
#                     "time": checkout_time_str,
#                     "name": full_name,
#                     "total_hours": total_hours_rounded,
#                     "overtime_hours": ot_hours_rounded,
#                     "is_late": info.get("is_late", False),
#                     "late_note": info.get("late_note", ""),
#                     "checkin_time": info.get("time", ""),
#                 }
#                 save_lock(lock)
#                 ot_line = f"   Overtime: {ot_str}" if ot_hours else ""
#                 # Check if early checkout
#                 early_limit = now.replace(
#                     hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
#                     second=0, microsecond=0)
#                 early_note = ""
#                 if now < early_limit:
#                     early_note = (f"\n   ⚠ Early checkout "
#                                   f"(before {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d})")
#                 return True, (
#                     f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}\n"
#                     f"   Total time: {total_str}\n"
#                     f"{ot_line}{early_note}")
#             errors = body.get("error", body.get("message", ""))
#             return False, (
#                 f"Zoho rejected the update (code {code}).\n"
#                 f"Error: {errors}\n"
#                 f"Worker: {full_name} Hours sent: {total_hours_rounded}")
#         return False, f"Check-out PATCH failed (HTTP {http_code}): {body_raw}"
#     return False, "Unknown action."

# # ===========================================================
# # DAILY SUMMARY EXPORT
# # ===========================================================
# def export_daily_summary():
#     lock     = load_lock()
#     today    = lock.get("date", datetime.now().strftime("%Y-%m-%d"))
#     filename = f"attendance_{today}.csv"
#     rows     = []
#     early_limit = datetime.now().replace(
#         hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
#         second=0, microsecond=0)

#     for zk_id, info in lock.get("checked_out", {}).items():
#         co_str = info.get("time", "")
#         is_early = False
#         try:
#             co_dt = datetime.strptime(co_str, "%H:%M:%S").replace(
#                 year=datetime.now().year, month=datetime.now().month,
#                 day=datetime.now().day)
#             is_early = co_dt < early_limit
#         except Exception:
#             pass
#         rows.append({
#             "ZK_ID": zk_id, "Name": info.get("name",""),
#             "Check-In": info.get("checkin_time",""), "Check-Out": co_str,
#             "Total Hours": info.get("total_hours",""),
#             "Overtime Hours": info.get("overtime_hours", 0),
#             "Late?": "Yes" if info.get("is_late") else "No",
#             "Late Note": info.get("late_note",""),
#             "Early Checkout?": "Yes" if is_early else "No",
#             "Status": "Complete",
#         })
#     for zk_id, info in lock.get("checked_in", {}).items():
#         rows.append({
#             "ZK_ID": zk_id, "Name": info.get("name",""),
#             "Check-In": info.get("time",""), "Check-Out": "—",
#             "Total Hours": "—", "Overtime Hours": "—",
#             "Late?": "Yes" if info.get("is_late") else "No",
#             "Late Note": info.get("late_note",""),
#             "Early Checkout?": "—", "Status": "Still In",
#         })
#     if not rows: return None
#     fieldnames = ["ZK_ID","Name","Check-In","Check-Out","Total Hours",
#                   "Overtime Hours","Late?","Late Note","Early Checkout?","Status"]
#     with open(filename, "w", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(rows)
#     return filename

# # ===========================================================
# # COLOUR PALETTE
# # ===========================================================
# BG          = "#07090f"
# CARD        = "#0c1018"
# CARD2       = "#10151f"
# CARD3       = "#141b27"
# BORDER      = "#1c2438"
# BORDER2     = "#243048"
# ACCENT      = "#3b82f6"
# ACCENT_DIM  = "#172554"
# ACCENT2     = "#60a5fa"
# GREEN       = "#10b981"
# GREEN2      = "#34d399"
# GREEN_DIM   = "#052e1c"
# RED         = "#f43f5e"
# RED2        = "#fb7185"
# RED_DIM     = "#4c0519"
# ORANGE      = "#f59e0b"
# ORANGE2     = "#fbbf24"
# ORANGE_DIM  = "#3d1f00"
# CYAN        = "#06b6d4"
# CYAN2       = "#67e8f9"
# CYAN_DIM    = "#083344"
# TEXT        = "#e2e8f0"
# TEXT2       = "#94a3b8"
# MUTED       = "#3d4f69"
# WHITE       = "#ffffff"
# GOLD        = "#f59e0b"
# GOLD2       = "#fde68a"
# PURPLE      = "#a78bfa"
# PURPLE_DIM  = "#2e1065"

# # ===========================================================
# # SHARED UI HELPERS
# # ===========================================================
# def _btn_hover(btn, bg_on, fg_on, bg_off, fg_off):
#     btn.bind("<Enter>",  lambda _: btn.config(bg=bg_on,  fg=fg_on))
#     btn.bind("<Leave>",  lambda _: btn.config(bg=bg_off, fg=fg_off))

# def _make_sep(parent, color=BORDER, height=1):
#     tk.Frame(parent, bg=color, height=height).pack(fill=tk.X)

# def _initials(name):
#     parts = name.strip().split()
#     if not parts:      return "??"
#     if len(parts) == 1: return parts[0][:2].upper()
#     return (parts[0][0] + parts[-1][0]).upper()

# # ===========================================================
# # FINGERPRINT CANVAS WIDGET
# # ===========================================================
# class FingerprintCanvas(tk.Canvas):
#     """
#     Animated fingerprint visual — concentric arcs that rotate
#     when scanning, pulse green on success, flash red on error.
#     """
#     SIZE = 140

#     def __init__(self, parent, **kwargs):
#         super().__init__(parent, width=self.SIZE, height=self.SIZE,
#                          bg=CARD2, highlightthickness=0, **kwargs)
#         self._cx = self._cy = self.SIZE // 2
#         self._angle  = 0
#         self._active = False
#         self._state  = "idle"   # idle | scanning | ok | error
#         self._phase  = 0
#         self._items  = []
#         self._draw_base()
#         self._animate()

#     def _draw_base(self):
#         """Draw the static fingerprint-like concentric arc skeleton."""
#         cx, cy = self._cx, self._cy
#         self.delete("fp")
#         # Outer glow ring
#         self.create_oval(cx-64, cy-64, cx+64, cy+64,
#                          outline=BORDER2, width=1, tags="fp")
#         # Fingerprint arcs — alternating open arcs to mimic ridge lines
#         arc_defs = [
#             (10, 0,   300, 2),
#             (18, 20,  280, 2),
#             (26, 30,  270, 1),
#             (34, 15,  290, 1),
#             (42, 25,  265, 1),
#             (50, 10,  285, 1),
#             (58, 35,  250, 1),
#         ]
#         self._arc_items = []
#         for r, start, extent, w in arc_defs:
#             item = self.create_arc(
#                 cx-r, cy-r, cx+r, cy+r,
#                 start=start, extent=extent,
#                 outline=MUTED, width=w, style="arc", tags="fp")
#             self._arc_items.append(item)
#         # Centre dot
#         self._centre = self.create_oval(
#             cx-5, cy-5, cx+5, cy+5,
#             fill=MUTED, outline="", tags="fp")
#         # Spinning scan arc (hidden by default)
#         self._spin = self.create_arc(
#             cx-58, cy-58, cx+58, cy+58,
#             start=0, extent=0,
#             outline=ACCENT, width=3, style="arc", tags="fp")

#     def start(self):
#         self._state  = "scanning"
#         self._active = True

#     def stop_ok(self):
#         self._state  = "ok"
#         self._active = False
#         self._flash_ok()

#     def stop_err(self, msg="ERROR"):
#         self._state  = "error"
#         self._active = False
#         self._flash_err()

#     def reset(self):
#         self._state  = "idle"
#         self._active = False
#         self._angle  = 0
#         self._draw_base()

#     def _flash_ok(self):
#         cx, cy = self._cx, self._cy
#         for item in self._arc_items:
#             self.itemconfig(item, outline=GREEN2)
#         self.itemconfig(self._centre, fill=GREEN2)
#         self.itemconfig(self._spin, extent=0)

#     def _flash_err(self):
#         cx, cy = self._cx, self._cy
#         for item in self._arc_items:
#             self.itemconfig(item, outline=RED2)
#         self.itemconfig(self._centre, fill=RED2)
#         self.itemconfig(self._spin, extent=0)

#     def _animate(self):
#         self._phase = (self._phase + 1) % 120
#         cx, cy = self._cx, self._cy

#         if self._state == "scanning":
#             self._angle = (self._angle + 6) % 360
#             # Sweep arc
#             sweep = int(200 * abs(math.sin(math.radians(self._angle))))
#             self.itemconfig(self._spin,
#                             start=self._angle, extent=sweep,
#                             outline=ACCENT)
#             # Pulse arcs
#             alpha = 0.4 + 0.6 * abs(math.sin(math.radians(self._phase * 3)))
#             r_val = int(int(ACCENT[1:3], 16) * alpha)
#             g_val = int(int(ACCENT[3:5], 16) * alpha)
#             b_val = int(int(ACCENT[5:7], 16) * alpha)
#             col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
#             for i, item in enumerate(self._arc_items):
#                 phase_offset = self._phase + i * 10
#                 a2 = 0.3 + 0.7 * abs(math.sin(math.radians(phase_offset * 4)))
#                 r2 = int(int(ACCENT[1:3], 16) * a2)
#                 g2 = int(int(ACCENT[3:5], 16) * a2)
#                 b2 = int(int(ACCENT[5:7], 16) * a2)
#                 self.itemconfig(item, outline=f"#{r2:02x}{g2:02x}{b2:02x}")
#             self.itemconfig(self._centre, fill=col)

#         elif self._state == "ok":
#             # Gentle pulse green
#             alpha = 0.6 + 0.4 * abs(math.sin(math.radians(self._phase * 2)))
#             r_val = int(int(GREEN2[1:3], 16) * alpha)
#             g_val = int(int(GREEN2[3:5], 16) * alpha)
#             b_val = int(int(GREEN2[5:7], 16) * alpha)
#             col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
#             for item in self._arc_items:
#                 self.itemconfig(item, outline=col)
#             self.itemconfig(self._centre, fill=col)

#         elif self._state == "error":
#             # Flash red
#             alpha = 0.4 + 0.6 * abs(math.sin(math.radians(self._phase * 6)))
#             r_val = int(int(RED2[1:3], 16) * alpha)
#             g_val = int(int(RED2[3:5], 16) * alpha)
#             b_val = int(int(RED2[5:7], 16) * alpha)
#             col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
#             for item in self._arc_items:
#                 self.itemconfig(item, outline=col)
#             self.itemconfig(self._centre, fill=col)

#         else:  # idle — slow breath
#             alpha = 0.25 + 0.20 * abs(math.sin(math.radians(self._phase * 1.5)))
#             r_val = int(int(MUTED[1:3], 16) * alpha * 2.5)
#             g_val = int(int(MUTED[3:5], 16) * alpha * 2.5)
#             b_val = int(int(MUTED[5:7], 16) * alpha * 2.5)
#             col = f"#{min(r_val,255):02x}{min(g_val,255):02x}{min(b_val,255):02x}"
#             for item in self._arc_items:
#                 self.itemconfig(item, outline=col)
#             self.itemconfig(self._spin, extent=0)

#         self.after(30, self._animate)

# # ===========================================================
# # PULSING LED
# # ===========================================================
# class PulseLED(tk.Canvas):
#     SIZE = 12
#     def __init__(self, parent, color=ACCENT):
#         super().__init__(parent, width=self.SIZE, height=self.SIZE,
#                          bg=parent.cget("bg"), highlightthickness=0)
#         r = self.SIZE // 2
#         self._dot   = self.create_oval(2, 2, r*2-2, r*2-2, fill=color, outline="")
#         self._color = color
#         self._phase = 0
#         self._pulse()

#     def set_color(self, color):
#         self._color = color
#         self.itemconfig(self._dot, fill=color)

#     def _pulse(self):
#         self._phase = (self._phase + 1) % 60
#         alpha = 0.55 + 0.45 * abs((self._phase % 60) - 30) / 30
#         c = self._color
#         try:
#             r = int(int(c[1:3], 16) * alpha)
#             g = int(int(c[3:5], 16) * alpha)
#             b = int(int(c[5:7], 16) * alpha)
#             self.itemconfig(self._dot, fill=f"#{r:02x}{g:02x}{b:02x}")
#         except Exception:
#             pass
#         self.after(50, self._pulse)

# # ===========================================================
# # DASHBOARD KPI RING (donut chart on canvas)
# # ===========================================================
# class DonutRing(tk.Canvas):
#     """Mini donut chart showing checked-in vs checked-out ratio."""
#     SIZE = 80

#     def __init__(self, parent, **kwargs):
#         super().__init__(parent, width=self.SIZE, height=self.SIZE,
#                          bg=CARD2, highlightthickness=0, **kwargs)
#         self._val = 0   # 0..1 fill
#         self._phase = 0
#         self._color = GREEN2
#         self._draw(0)
#         self._tick()

#     def set_value(self, fraction, color=GREEN2):
#         self._val   = max(0.0, min(1.0, fraction))
#         self._color = color
#         self._draw(self._val)

#     def _draw(self, fraction):
#         self.delete("all")
#         cx = cy = self.SIZE // 2
#         r  = cx - 6
#         # Background ring
#         self.create_arc(cx-r, cy-r, cx+r, cy+r,
#                         start=0, extent=359.9,
#                         outline=BORDER2, width=10, style="arc")
#         # Value arc
#         if fraction > 0:
#             ext = fraction * 359.9
#             alpha = 0.7 + 0.3 * abs(math.sin(math.radians(self._phase * 2)))
#             self.create_arc(cx-r, cy-r, cx+r, cy+r,
#                             start=90, extent=-ext,
#                             outline=self._color, width=10, style="arc")
#         # Centre text
#         pct = int(fraction * 100)
#         self.create_text(cx, cy, text=f"{pct}%",
#                          font=("Courier", 11, "bold"),
#                          fill=self._color if fraction > 0 else MUTED)

#     def _tick(self):
#         self._phase += 1
#         self._draw(self._val)
#         self.after(100, self._tick)

# # ===========================================================
# # ADMIN PANEL
# # ===========================================================
# class AdminPanel(tk.Toplevel):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.title("Attendance Command Center")
#         self.configure(bg=BG)
#         self.resizable(True, True)
#         sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
#         W, H   = min(sw, 1150), min(sh, 700)
#         self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
#         self._build()
#         self.refresh()

#     def _build(self):
#         # Header
#         hdr = tk.Frame(self, bg=CARD)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=PURPLE, height=2).pack(fill=tk.X)
#         hi = tk.Frame(hdr, bg=CARD, padx=24, pady=14)
#         hi.pack(fill=tk.X)
#         lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="ATTENDANCE COMMAND CENTER",
#                  font=("Courier", 13, "bold"), bg=CARD, fg=PURPLE).pack(anchor="w")
#         self.sub_lbl = tk.Label(lf, text="", font=("Courier", 8), bg=CARD, fg=TEXT2)
#         self.sub_lbl.pack(anchor="w", pady=(2, 0))
#         rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
#         for txt, cmd, bg_, fg_ in [
#             ("↻ REFRESH", self.refresh, ACCENT_DIM, ACCENT2),
#             ("⬇ EXPORT CSV", self._export, GREEN_DIM, GREEN2),
#             ("✕ CLOSE", self.destroy, BORDER, TEXT2),
#         ]:
#             b = tk.Button(rf, text=txt, font=("Courier", 9, "bold"),
#                           relief=tk.FLAT, bg=bg_, fg=fg_, cursor="hand2",
#                           padx=14, pady=6, command=cmd)
#             b.pack(side=tk.LEFT, padx=(0, 6))

#         # KPI tiles
#         self.kpi_fr = tk.Frame(self, bg=BG, padx=20, pady=12)
#         self.kpi_fr.pack(fill=tk.X)

#         _make_sep(self, BORDER2)

#         # Table
#         tree_wrap = tk.Frame(self, bg=BG, padx=20, pady=12)
#         tree_wrap.pack(fill=tk.BOTH, expand=True)
#         style = ttk.Style(self)
#         style.theme_use("default")
#         style.configure("Cmd.Treeview", background=CARD2, foreground=TEXT,
#                          fieldbackground=CARD2, rowheight=30,
#                          font=("Courier", 9), borderwidth=0)
#         style.configure("Cmd.Treeview.Heading", background=CARD,
#                          foreground=GOLD, font=("Courier", 9, "bold"),
#                          relief="flat", borderwidth=0)
#         style.map("Cmd.Treeview",
#                   background=[("selected", ACCENT_DIM)],
#                   foreground=[("selected", ACCENT2)])
#         cols    = ("Initials","Name","Check-In","Check-Out","Hours","Overtime","Early Out?","Late","Status")
#         widths  = (60, 190, 110, 110, 80, 90, 90, 80, 90)
#         anchors = ("center","w","center","center","center","center","center","center","center")
#         self.tree = ttk.Treeview(tree_wrap, columns=cols,
#                                  show="headings", style="Cmd.Treeview",
#                                  selectmode="browse")
#         for col, w, a in zip(cols, widths, anchors):
#             self.tree.heading(col, text=col.upper())
#             self.tree.column(col, width=w, anchor=a, stretch=(col == "Name"))
#         self.tree.tag_configure("late",     foreground=ORANGE2)
#         self.tree.tag_configure("ot",       foreground=PURPLE)
#         self.tree.tag_configure("complete", foreground=GREEN2)
#         self.tree.tag_configure("still_in", foreground=ACCENT2)
#         self.tree.tag_configure("early",    foreground=CYAN2)
#         self.tree.tag_configure("alt",      background="#0e1320")
#         vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
#         self.tree.configure(yscrollcommand=vsb.set)
#         self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         vsb.pack(side=tk.RIGHT, fill=tk.Y)

#     def refresh(self):
#         for row in self.tree.get_children():
#             self.tree.delete(row)
#         lock        = load_lock()
#         checked_in  = lock.get("checked_in",  {})
#         checked_out = lock.get("checked_out", {})
#         total       = len(checked_in) + len(checked_out)
#         late_count  = ot_count = early_count = 0
#         now         = datetime.now()
#         early_limit = now.replace(hour=EARLY_CHECKOUT_H,
#                                   minute=EARLY_CHECKOUT_M,
#                                   second=0, microsecond=0)
#         row_idx = 0

#         def _insert(values, tags):
#             nonlocal row_idx
#             if row_idx % 2 == 1:
#                 tags = list(tags) + ["alt"]
#             self.tree.insert("", tk.END, values=values, tags=tuple(tags))
#             row_idx += 1

#         for zk_id, info in sorted(checked_out.items(),
#                                    key=lambda x: x[1].get("checkin_time", "")):
#             name    = info.get("name", zk_id)
#             ci      = info.get("checkin_time", "—")
#             ci_s    = ci[-8:] if len(ci) > 8 else ci
#             co      = info.get("time", "—")
#             hrs     = info.get("total_hours", 0)
#             ot      = info.get("overtime_hours", 0)
#             late    = info.get("is_late", False)
#             h_str   = f"{int(hrs)}h {int((hrs%1)*60):02d}m" if isinstance(hrs,(int,float)) else str(hrs)
#             o_str   = f"{int(ot)}h {int((ot%1)*60):02d}m" if ot else "—"
#             # Early checkout?
#             is_early = False
#             try:
#                 co_dt = datetime.strptime(co, "%H:%M:%S").replace(
#                     year=now.year, month=now.month, day=now.day)
#                 is_early = co_dt < early_limit
#             except Exception:
#                 pass
#             if late:    late_count  += 1
#             if ot > 0:  ot_count    += 1
#             if is_early: early_count += 1
#             tags = []
#             if late:     tags.append("late")
#             if ot > 0:   tags.append("ot")
#             if is_early: tags.append("early")
#             tags.append("complete")
#             _insert((_initials(name), name, ci_s, co, h_str, o_str,
#                      "⚡ EARLY" if is_early else "—",
#                      "⚠ LATE" if late else "—", "✔ DONE"), tags)

#         for zk_id, info in sorted(checked_in.items(),
#                                    key=lambda x: x[1].get("time", "")):
#             name = info.get("name", zk_id)
#             ci   = info.get("time", "—")
#             late = info.get("is_late", False)
#             try:
#                 dt_in   = datetime.strptime(ci, "%d-%b-%Y %H:%M:%S")
#                 elapsed = (now - dt_in).total_seconds() / 3600
#                 h_str   = f"{int(elapsed)}h {int((elapsed%1)*60):02d}m"
#             except Exception:
#                 h_str = "—"
#             ci_s = ci[-8:] if len(ci) > 8 else ci
#             if late: late_count += 1
#             tags = ["late"] if late else []
#             tags.append("still_in")
#             _insert((_initials(name), name, ci_s, "—", h_str, "—", "—",
#                      "⚠ LATE" if late else "—", "● ACTIVE"), tags)

#         # KPI tiles
#         for w in self.kpi_fr.winfo_children():
#             w.destroy()
#         kpis = [
#             ("TOTAL TODAY",      total,              WHITE,   BORDER2),
#             ("CHECKED IN",       len(checked_in) + len(checked_out), ACCENT2, "#0d1f3f"),
#             ("CHECKED OUT",      len(checked_out),   GREEN2,  "#0a3321"),
#             ("EARLY CHECKOUT",   early_count,         CYAN2,   CYAN_DIM),
#             ("LATE ARRIVALS",    late_count,           ORANGE2, "#3d1f00"),
#             ("OVERTIME",         ot_count,             PURPLE,  "#1e0a40"),
#         ]
#         for label, val, fg, border_col in kpis:
#             tile = tk.Frame(self.kpi_fr, bg=CARD2, padx=18, pady=10,
#                             highlightbackground=border_col, highlightthickness=1)
#             tile.pack(side=tk.LEFT, padx=(0, 10), fill=tk.Y)
#             tk.Label(tile, text=str(val), font=("Courier", 26, "bold"),
#                      bg=CARD2, fg=fg).pack()
#             tk.Label(tile, text=label, font=("Courier", 7, "bold"),
#                      bg=CARD2, fg=TEXT2).pack()
#         self.sub_lbl.config(
#             text=(f"Date: {lock.get('date','')}  "
#                   f"Shift: {SHIFT_START_H:02d}:{SHIFT_START_M:02d}  "
#                   f"Standard: {SHIFT_HOURS}h  "
#                   f"Grace: {GRACE_MINUTES}min  "
#                   f"Early Out before: {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d}  "
#                   f"Refreshed: {now.strftime('%H:%M:%S')}"))

#     def _export(self):
#         fname = export_daily_summary()
#         if fname:
#             messagebox.showinfo("Export Complete",
#                                 f"Saved to:\n{os.path.abspath(fname)}", parent=self)
#         else:
#             messagebox.showwarning("Nothing to Export",
#                                    "No attendance records for today.", parent=self)

# # ===========================================================
# # MAIN GUI
# # ===========================================================
# class FingerprintGUI:
#     def __init__(self, root):
#         self.root        = root
#         self.root.title("Wavemark Properties — Attendance Terminal")
#         self.root.configure(bg=BG)
#         self.root.resizable(False, False)
#         self._busy          = False
#         self._debounce_job  = None
#         self._worker_cache  = {}
#         sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
#         W, H   = min(sw, 980), min(sh, 800)
#         self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
#         self._build_ui()
#         self._tick_clock()
#         self._tick_stats()
#         self.root.protocol("WM_DELETE_WINDOW", self._on_close)

#     # ── BUILD ────────────────────────────────────────────
#     def _build_ui(self):
#         self._build_header()
#         self._build_body()
#         self._build_footer()
#         self._build_flash()

#     # ── HEADER ──────────────────────────────────────────
#     def _build_header(self):
#         hdr = tk.Frame(self.root, bg=CARD)
#         hdr.pack(fill=tk.X)
#         tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)
#         hi = tk.Frame(hdr, bg=CARD, padx=28, pady=14)
#         hi.pack(fill=tk.X)
#         lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
#         tk.Label(lf, text="WAVEMARK PROPERTIES LIMITED",
#                  font=("Courier", 11, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
#         tk.Label(lf, text="Biometric Attendance Terminal · v4.0",
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(1, 0))
#         rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
#         btn_admin = tk.Button(rf, text="⚙ ADMIN PANEL",
#                               font=("Courier", 8, "bold"), relief=tk.FLAT,
#                               bg=PURPLE_DIM, fg=PURPLE,
#                               activebackground=PURPLE, activeforeground=WHITE,
#                               cursor="hand2", padx=10, pady=5,
#                               command=self._open_admin)
#         btn_admin.pack(anchor="e", pady=(0, 6))
#         _btn_hover(btn_admin, PURPLE, WHITE, PURPLE_DIM, PURPLE)
#         self.date_lbl  = tk.Label(rf, text="", font=("Courier", 8),  bg=CARD, fg=TEXT2)
#         self.date_lbl.pack(anchor="e")
#         self.clock_lbl = tk.Label(rf, text="", font=("Courier", 24, "bold"), bg=CARD, fg=WHITE)
#         self.clock_lbl.pack(anchor="e")
#         _make_sep(self.root, BORDER2)
#         sbar = tk.Frame(self.root, bg=CARD2, padx=28, pady=6)
#         sbar.pack(fill=tk.X)
#         shift_txt = (f"SHIFT {SHIFT_START_H:02d}:{SHIFT_START_M:02d} · "
#                      f"STANDARD {SHIFT_HOURS}H · "
#                      f"GRACE {GRACE_MINUTES}MIN · "
#                      f"EARLY CHECKOUT BEFORE {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d}")
#         tk.Label(sbar, text=shift_txt, font=("Courier", 8), bg=CARD2, fg=MUTED).pack(side=tk.LEFT)
#         tk.Label(sbar, text="ENTER → auto-action   ESC → clear",
#                  font=("Courier", 8), bg=CARD2, fg=MUTED).pack(side=tk.RIGHT)

#     # ── BODY ────────────────────────────────────────────
#     def _build_body(self):
#         body = tk.Frame(self.root, bg=BG, padx=24, pady=14)
#         body.pack(fill=tk.BOTH, expand=True)
#         cols = tk.Frame(body, bg=BG)
#         cols.pack(fill=tk.BOTH, expand=True)
#         left  = tk.Frame(cols, bg=BG); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         vsep  = tk.Frame(cols, bg=BORDER, width=1); vsep.pack(side=tk.LEFT, fill=tk.Y, padx=16)
#         right = tk.Frame(cols, bg=BG, width=300); right.pack(side=tk.LEFT, fill=tk.Y)
#         self._build_left(left)
#         self._build_right(right)

#     def _build_left(self, parent):
#         # ── Worker ID card ────────────────────────────
#         id_card = tk.Frame(parent, bg=CARD2,
#                            highlightbackground=BORDER2, highlightthickness=1)
#         id_card.pack(fill=tk.X, pady=(0, 12))
#         ch = tk.Frame(id_card, bg=CARD, padx=18, pady=10); ch.pack(fill=tk.X)
#         tk.Label(ch, text="WORKER IDENTIFICATION",
#                  font=("Courier", 8, "bold"), bg=CARD, fg=TEXT2).pack(side=tk.LEFT)
#         self._led = PulseLED(ch, MUTED); self._led.pack(side=tk.RIGHT, padx=(0, 2))
#         _make_sep(id_card, BORDER)
#         ci = tk.Frame(id_card, bg=CARD2, padx=18, pady=14); ci.pack(fill=tk.X)
#         er = tk.Frame(ci, bg=CARD2); er.pack(fill=tk.X)
#         tk.Label(er, text="ID", font=("Courier", 8, "bold"),
#                  bg=CARD2, fg=MUTED, width=3, anchor="w").pack(side=tk.LEFT)
#         eb = tk.Frame(er, bg=GOLD, padx=1, pady=1); eb.pack(side=tk.LEFT, padx=(6, 0))
#         ei = tk.Frame(eb, bg="#09101a"); ei.pack()
#         self.user_entry = tk.Entry(ei, font=("Courier", 28, "bold"), width=9,
#                                    bd=0, bg="#09101a", fg=WHITE,
#                                    insertbackground=GOLD,
#                                    selectbackground=GOLD2, selectforeground=BG)
#         self.user_entry.pack(padx=14, pady=8)
#         self.user_entry.bind("<KeyRelease>",  self._on_key)
#         self.user_entry.bind("<Return>",      self._on_enter)
#         self.user_entry.bind("<Escape>",      lambda _: self._reset_ui())
#         self.user_entry.focus_set()
#         btn_clr = tk.Button(er, text="✕", font=("Courier", 10, "bold"),
#                             relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                             activebackground=RED_DIM, activeforeground=RED,
#                             cursor="hand2", padx=8, pady=4, command=self._reset_ui)
#         btn_clr.pack(side=tk.LEFT, padx=(10, 0))
#         _btn_hover(btn_clr, RED_DIM, RED, BORDER, MUTED)
#         # Identity row
#         idf = tk.Frame(ci, bg=CARD2); idf.pack(fill=tk.X, pady=(12, 0))
#         self._avatar_cv = tk.Canvas(idf, width=48, height=48, bg=CARD2, highlightthickness=0)
#         self._avatar_cv.pack(side=tk.LEFT, padx=(0, 12))
#         self._avatar_circle = self._avatar_cv.create_oval(2,2,46,46, fill=BORDER, outline="")
#         self._avatar_text   = self._avatar_cv.create_text(24,24, text="",
#                                                            font=("Courier", 13, "bold"),
#                                                            fill=MUTED)
#         info_col = tk.Frame(idf, bg=CARD2); info_col.pack(side=tk.LEFT, fill=tk.X)
#         self.name_lbl = tk.Label(info_col, text="—",
#                                   font=("Courier", 16, "bold"), bg=CARD2, fg=MUTED)
#         self.name_lbl.pack(anchor="w")
#         self.hint_lbl = tk.Label(info_col, text="Enter a Worker ID above",
#                                   font=("Courier", 9), bg=CARD2, fg=MUTED)
#         self.hint_lbl.pack(anchor="w", pady=(2, 0))

#         # ── Status banner ─────────────────────────────
#         self.sf = tk.Frame(parent, bg=ACCENT_DIM,
#                            highlightbackground=ACCENT, highlightthickness=1)
#         self.sf.pack(fill=tk.X, pady=(0, 12))
#         sb_inner = tk.Frame(self.sf, bg=ACCENT_DIM); sb_inner.pack(fill=tk.X, padx=16, pady=10)
#         self._status_led = PulseLED(sb_inner, ACCENT); self._status_led.pack(side=tk.LEFT, padx=(0,8))
#         self.sl = tk.Label(sb_inner, text="Awaiting Worker ID",
#                            font=("Courier", 10, "bold"), bg=ACCENT_DIM, fg=ACCENT, anchor="w")
#         self.sl.pack(side=tk.LEFT, fill=tk.X)

#         # ── Action buttons ────────────────────────────
#         br = tk.Frame(parent, bg=BG); br.pack(fill=tk.X, pady=(0, 12))
#         self.btn_in = tk.Button(br, text="▶ CHECK IN",
#                                 font=("Courier", 12, "bold"), width=15, relief=tk.FLAT,
#                                 bg=GREEN_DIM, fg=MUTED,
#                                 activebackground=GREEN, activeforeground=BG,
#                                 cursor="hand2", state=tk.DISABLED,
#                                 command=lambda: self._trigger("checkin"))
#         self.btn_in.pack(side=tk.LEFT, ipady=12, padx=(0, 10))
#         self.btn_out = tk.Button(br, text="◼ CHECK OUT",
#                                  font=("Courier", 12, "bold"), width=15, relief=tk.FLAT,
#                                  bg=RED_DIM, fg=MUTED,
#                                  activebackground=RED, activeforeground=WHITE,
#                                  cursor="hand2", state=tk.DISABLED,
#                                  command=lambda: self._trigger("checkout"))
#         self.btn_out.pack(side=tk.LEFT, ipady=12, padx=(0, 10))
#         btn_exp = tk.Button(br, text="⬇", font=("Courier", 11, "bold"),
#                             relief=tk.FLAT, bg=BORDER, fg=TEXT2,
#                             cursor="hand2", padx=12, command=self._quick_export)
#         btn_exp.pack(side=tk.RIGHT, ipady=12)
#         _btn_hover(btn_exp, GREEN_DIM, GREEN2, BORDER, TEXT2)

#         _make_sep(parent, BORDER, height=1)
#         tk.Frame(parent, bg=BG, height=8).pack()

#         # ── Activity log ──────────────────────────────
#         lh = tk.Frame(parent, bg=BG); lh.pack(fill=tk.X, pady=(0, 6))
#         tk.Label(lh, text="ACTIVITY LOG", font=("Courier", 8, "bold"),
#                  bg=BG, fg=MUTED).pack(side=tk.LEFT)
#         btn_clrlog = tk.Button(lh, text="CLEAR", font=("Courier", 7, "bold"),
#                                relief=tk.FLAT, bg=BORDER, fg=MUTED,
#                                padx=8, pady=2, cursor="hand2", command=self._clear_log)
#         btn_clrlog.pack(side=tk.RIGHT)
#         _btn_hover(btn_clrlog, BORDER2, TEXT2, BORDER, MUTED)
#         lw = tk.Frame(parent, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
#         lw.pack(fill=tk.BOTH, expand=True)
#         sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD); sb.pack(side=tk.RIGHT, fill=tk.Y)
#         self.log_box = tk.Text(lw, font=("Courier", 9), bg=CARD, fg=TEXT2,
#                                relief=tk.FLAT, padx=14, pady=10,
#                                yscrollcommand=sb.set, state=tk.DISABLED, cursor="arrow")
#         self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         sb.config(command=self.log_box.yview)
#         for tag, col in [("ok", GREEN2), ("err", RED2), ("warn", ORANGE2),
#                           ("info", ACCENT2), ("ts", MUTED), ("div", BORDER2),
#                           ("late", ORANGE), ("ot", PURPLE), ("early", CYAN2)]:
#             self.log_box.tag_config(tag, foreground=col)

#     def _build_right(self, parent):
#         """Right panel: fingerprint + live dashboard."""
#         # ── Fingerprint visual ────────────────────────
#         fp_lbl = tk.Label(parent, text="BIOMETRIC SCANNER",
#                           font=("Courier", 8, "bold"), bg=BG, fg=MUTED)
#         fp_lbl.pack(anchor="w", pady=(0, 8))
#         sc = tk.Frame(parent, bg=CARD2,
#                       highlightbackground=BORDER2, highlightthickness=1)
#         sc.pack(fill=tk.X, pady=(0, 14))
#         sc_inner = tk.Frame(sc, bg=CARD2, pady=16); sc_inner.pack()
#         self._fp = FingerprintCanvas(sc_inner)
#         self._fp.pack(pady=(0, 8))
#         self._scan_lbl = tk.Label(sc_inner, text="READY",
#                                   font=("Courier", 9, "bold"), bg=CARD2, fg=MUTED)
#         self._scan_lbl.pack()
#         self._scan_sub = tk.Label(sc_inner, text="Place finger when prompted",
#                                   font=("Courier", 7), bg=CARD2, fg=MUTED, wraplength=200)
#         self._scan_sub.pack(pady=(2, 0))

#         # ── LIVE DASHBOARD ────────────────────────────
#         tk.Label(parent, text="LIVE DASHBOARD",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 8))

#         dash = tk.Frame(parent, bg=BG)
#         dash.pack(fill=tk.X)

#         # Row 1: Checked In | Checked Out
#         row1 = tk.Frame(dash, bg=BG); row1.pack(fill=tk.X, pady=(0, 8))

#         self._tile_checkedin  = self._make_dash_tile(row1, "CHECKED IN TODAY",  "0", ACCENT2, "#0d1f3f", side=tk.LEFT)
#         self._tile_checkedout = self._make_dash_tile(row1, "CHECKED OUT",       "0", GREEN2,  "#0a3321", side=tk.LEFT)

#         # Row 2: Early Checkout (full width highlight)
#         row2 = tk.Frame(dash, bg=BG); row2.pack(fill=tk.X, pady=(0, 8))
#         self._tile_early = self._make_dash_tile(row2, f"LEFT BEFORE {EARLY_CHECKOUT_H:02d}:00", "0",
#                                                  CYAN2, CYAN_DIM, side=tk.LEFT, full=True)

#         # Row 3: Late | Overtime
#         row3 = tk.Frame(dash, bg=BG); row3.pack(fill=tk.X, pady=(0, 8))
#         self._tile_late = self._make_dash_tile(row3, "LATE ARRIVALS", "0", ORANGE2, "#3d1f00", side=tk.LEFT)
#         self._tile_ot   = self._make_dash_tile(row3, "OVERTIME",      "0", PURPLE,  "#1e0a40", side=tk.LEFT)

#         # Donut ring showing completion rate
#         dr_frame = tk.Frame(parent, bg=CARD2,
#                             highlightbackground=BORDER, highlightthickness=1)
#         dr_frame.pack(fill=tk.X, pady=(0, 10))
#         dr_inner = tk.Frame(dr_frame, bg=CARD2, pady=10, padx=16); dr_inner.pack(fill=tk.X)
#         tk.Label(dr_inner, text="COMPLETION RATE",
#                  font=("Courier", 7, "bold"), bg=CARD2, fg=MUTED).pack(anchor="w", pady=(0,6))
#         dr_row = tk.Frame(dr_inner, bg=CARD2); dr_row.pack(fill=tk.X)
#         self._donut = DonutRing(dr_row)
#         self._donut.pack(side=tk.LEFT, padx=(0, 14))
#         dr_legend = tk.Frame(dr_row, bg=CARD2); dr_legend.pack(side=tk.LEFT, fill=tk.Y)
#         self._legend_lbl = tk.Label(dr_legend, text="0 of 0 workers\nhave checked out",
#                                      font=("Courier", 8), bg=CARD2, fg=TEXT2,
#                                      justify=tk.LEFT)
#         self._legend_lbl.pack(anchor="w")
#         self._early_lbl = tk.Label(dr_legend, text="",
#                                     font=("Courier", 8), bg=CARD2, fg=CYAN2,
#                                     justify=tk.LEFT)
#         self._early_lbl.pack(anchor="w", pady=(6, 0))

#         # ── Recent events ─────────────────────────────
#         tk.Label(parent, text="RECENT EVENTS",
#                  font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(8, 6))
#         ev_fr = tk.Frame(parent, bg=CARD,
#                          highlightbackground=BORDER, highlightthickness=1)
#         ev_fr.pack(fill=tk.BOTH, expand=True)
#         self._event_box = tk.Text(ev_fr, font=("Courier", 8), bg=CARD, fg=TEXT2,
#                                    relief=tk.FLAT, padx=10, pady=8,
#                                    state=tk.DISABLED, cursor="arrow", height=7)
#         self._event_box.pack(fill=tk.BOTH, expand=True)
#         for tag, col in [("in", GREEN2), ("out", ACCENT2), ("warn", ORANGE2),
#                           ("ts", MUTED), ("early", CYAN2)]:
#             self._event_box.tag_config(tag, foreground=col)

#     def _make_dash_tile(self, parent, label, value, fg, bg2,
#                         side=tk.LEFT, full=False):
#         """Create a KPI tile and return the value Label for later update."""
#         tile = tk.Frame(parent, bg=CARD2, padx=14, pady=10,
#                         highlightbackground=bg2, highlightthickness=1)
#         if full:
#             tile.pack(side=side, fill=tk.X, expand=True)
#         else:
#             tile.pack(side=side, fill=tk.X, expand=True, padx=(0, 6) if side==tk.LEFT else 0)
#         val_lbl = tk.Label(tile, text=value,
#                            font=("Courier", 26, "bold"), bg=CARD2, fg=fg)
#         val_lbl.pack()
#         tk.Label(tile, text=label, font=("Courier", 6, "bold"),
#                  bg=CARD2, fg=TEXT2).pack()
#         return val_lbl

#     # ── FOOTER ──────────────────────────────────────────
#     def _build_footer(self):
#         _make_sep(self.root, BORDER2)
#         foot = tk.Frame(self.root, bg=CARD, padx=28, pady=7)
#         foot.pack(fill=tk.X, side=tk.BOTTOM)
#         self._foot_lbl = tk.Label(foot, text="", font=("Courier", 8), bg=CARD, fg=MUTED)
#         self._foot_lbl.pack(side=tk.LEFT)
#         tk.Label(foot, text=(f"Shift {SHIFT_START_H:02d}:{SHIFT_START_M:02d} – "
#                               f"{(SHIFT_START_H+SHIFT_HOURS)%24:02d}:{SHIFT_START_M:02d} "
#                               f"· {SHIFT_HOURS}h standard · {GRACE_MINUTES}min grace · "
#                               f"Early out < {EARLY_CHECKOUT_H:02d}:00"),
#                  font=("Courier", 8), bg=CARD, fg=MUTED).pack(side=tk.RIGHT)

#     # ── FLASH OVERLAY ───────────────────────────────────
#     def _build_flash(self):
#         self.flash = tk.Frame(self.root, bg=ACCENT)
#         self.fi = tk.Label(self.flash, font=("Courier", 60, "bold"), bg=ACCENT, fg=WHITE)
#         self.fi.place(relx=0.5, rely=0.28, anchor="center")
#         self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
#                            bg=ACCENT, fg=WHITE, wraplength=740)
#         self.fm.place(relx=0.5, rely=0.45, anchor="center")
#         self.fs = tk.Label(self.flash, font=("Courier", 12),
#                            bg=ACCENT, fg="#c7d9ff", wraplength=740)
#         self.fs.place(relx=0.5, rely=0.56, anchor="center")
#         self.fx = tk.Label(self.flash, font=("Courier", 11, "bold"),
#                            bg=ACCENT, fg=GOLD2, wraplength=740)
#         self.fx.place(relx=0.5, rely=0.65, anchor="center")

#     # ── CLOCK ───────────────────────────────────────────
#     def _tick_clock(self):
#         n = datetime.now()
#         self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
#         self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
#         self.root.after(1000, self._tick_clock)

#     # ── LIVE STATS ──────────────────────────────────────
#     def _tick_stats(self):
#         lock  = load_lock()
#         cin   = lock.get("checked_in",  {})
#         cout  = lock.get("checked_out", {})
#         total = len(cin) + len(cout)

#         # All who checked in today (in + out)
#         total_in  = total
#         total_out = len(cout)
#         early     = count_early_checkouts(lock)
#         late      = sum(1 for v in {**cin, **cout}.values()
#                         if isinstance(v, dict) and v.get("is_late"))
#         ot        = sum(1 for v in cout.values()
#                         if isinstance(v, dict) and v.get("overtime_hours", 0) > 0)

#         # Update tiles
#         self._tile_checkedin.config(text=str(total_in))
#         self._tile_checkedout.config(text=str(total_out))
#         self._tile_early.config(text=str(early))
#         self._tile_late.config(text=str(late))
#         self._tile_ot.config(text=str(ot))

#         # Donut
#         fraction = (total_out / total_in) if total_in > 0 else 0
#         donut_color = GREEN2 if fraction >= 0.8 else ORANGE2 if fraction >= 0.4 else ACCENT2
#         self._donut.set_value(fraction, donut_color)
#         self._legend_lbl.config(
#             text=f"{total_out} of {total_in} workers\nhave checked out")
#         if early > 0:
#             self._early_lbl.config(
#                 text=f"⚡ {early} left before {EARLY_CHECKOUT_H:02d}:00")
#         else:
#             self._early_lbl.config(text="")

#         self._foot_lbl.config(
#             text=(f"Checked In: {total_in}  "
#                   f"Out: {total_out}  "
#                   f"On-site: {len(cin)}  "
#                   f"Early: {early}  "
#                   f"Late: {late}  "
#                   f"OT: {ot}"))

#         self.root.after(6000, self._tick_stats)

#     # ── ADMIN ───────────────────────────────────────────
#     def _open_admin(self): AdminPanel(self.root)

#     # ── EXPORT ──────────────────────────────────────────
#     def _quick_export(self):
#         fname = export_daily_summary()
#         if fname:
#             self.log(f"Exported → {os.path.abspath(fname)}", "ok")
#             self._add_event("Export", fname, "ts")
#         else:
#             self.log("Nothing to export — no records today.", "warn")

#     # ── LOGGING ─────────────────────────────────────────
#     def log(self, msg, tag="info"):
#         def _do():
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] ", "ts")
#             self.log_box.insert(tk.END, f"{msg}\n", tag)
#             self.log_box.see(tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     def _clear_log(self):
#         self.log_box.config(state=tk.NORMAL)
#         self.log_box.delete("1.0", tk.END)
#         self.log_box.config(state=tk.DISABLED)

#     def _add_event(self, action, name, tag="ts"):
#         def _do():
#             self._event_box.config(state=tk.NORMAL)
#             ts = datetime.now().strftime("%H:%M")
#             self._event_box.insert("1.0", f"{ts} {action:<10} {name}\n", tag)
#             self._event_box.config(state=tk.DISABLED)
#         self.root.after(0, _do)

#     # ── FLASH ───────────────────────────────────────────
#     def _show_flash(self, icon, headline, sub, extra, color):
#         self.flash.config(bg=color)
#         for w, v in [(self.fi, icon), (self.fm, headline),
#                      (self.fs, sub), (self.fx, extra)]:
#             w.config(text=v, bg=color)
#         self.flash.place(x=0, y=0, relwidth=1, relheight=1)
#         self.flash.lift()
#         self.root.after(2400, self.flash.place_forget)

#     # ── SCANNER UI ──────────────────────────────────────
#     def _scan_start(self):
#         self._fp.start()
#         self._scan_lbl.config(text="SCANNING…", fg=ORANGE2)
#         self._scan_sub.config(text="Place your finger on the reader now")

#     def _scan_ok(self):
#         self._fp.stop_ok()
#         self._scan_lbl.config(text="CAPTURED ✔", fg=GREEN2)
#         self._scan_sub.config(text="Processing…")

#     def _scan_err(self, msg="FAILED"):
#         self._fp.stop_err(msg)
#         self._scan_lbl.config(text=msg, fg=RED2)
#         self._scan_sub.config(text="Please try again")

#     def _scan_reset(self):
#         self._fp.reset()
#         self._scan_lbl.config(text="READY", fg=MUTED)
#         self._scan_sub.config(text="Place finger when prompted")

#     # ── STATUS & BUTTONS ────────────────────────────────
#     def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
#         def _do():
#             self.sf.config(bg=bg, highlightbackground=border)
#             for w in self.sf.winfo_children():
#                 for iw in ([w] + list(w.winfo_children())):
#                     try: iw.config(bg=bg)
#                     except Exception: pass
#             self.sl.config(text=text, fg=fg, bg=bg)
#             self._status_led.config(bg=bg)
#             self._status_led.set_color(fg)
#             self._led.set_color(fg)
#         self.root.after(0, _do)

#     def _set_buttons(self, in_s, out_s):
#         def _do():
#             self.btn_in.config(
#                 state=in_s,
#                 bg=GREEN if in_s == tk.NORMAL else GREEN_DIM,
#                 fg=BG    if in_s == tk.NORMAL else MUTED)
#             self.btn_out.config(
#                 state=out_s,
#                 bg=RED   if out_s == tk.NORMAL else RED_DIM,
#                 fg=WHITE if out_s == tk.NORMAL else MUTED)
#         self.root.after(0, _do)

#     def _set_avatar(self, name=None, color=BORDER):
#         initials = _initials(name) if name else ""
#         self._avatar_cv.itemconfig(self._avatar_circle, fill=color)
#         self._avatar_cv.itemconfig(self._avatar_text, text=initials,
#                                    fill=WHITE if name else MUTED)

#     def _apply_status(self, status, name=None):
#         if status == "done":
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Attendance complete — see you tomorrow", RED, RED_DIM, RED)
#             self._set_avatar(name, RED_DIM)
#         elif status == "checked_in":
#             self._set_buttons(tk.DISABLED, tk.NORMAL)
#             self._set_status("Already checked IN — proceed to Check-Out", ORANGE, ORANGE_DIM, ORANGE)
#             self._set_avatar(name, ORANGE_DIM)
#         elif status == "none":
#             self._set_buttons(tk.NORMAL, tk.DISABLED)
#             self._set_status("Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
#             self._set_avatar(name, GREEN_DIM)
#         else:
#             self._set_buttons(tk.DISABLED, tk.DISABLED)
#             self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
#             self._set_avatar(None, BORDER)

#     # ── ID VALIDATION ───────────────────────────────────
#     def _on_key(self, _=None):
#         if self._debounce_job:
#             self.root.after_cancel(self._debounce_job)
#         uid = self.user_entry.get().strip()
#         if not uid:
#             self._soft_reset(); return
#         self._apply_status(get_worker_status(uid))
#         self._debounce_job = self.root.after(
#             650, lambda: threading.Thread(
#                 target=self._validate, args=(uid,), daemon=True).start())

#     def _validate(self, uid):
#         if self.user_entry.get().strip() != uid or self._busy: return
#         worker = self._worker_cache.get(uid) or find_worker(uid)
#         if worker: self._worker_cache[uid] = worker
#         if self.user_entry.get().strip() != uid: return
#         def _upd():
#             if not worker:
#                 self.name_lbl.config(text="Unknown ID", fg=RED2)
#                 self.hint_lbl.config(text=f"ID '{uid}' not found — contact admin", fg=RED)
#                 self._set_buttons(tk.DISABLED, tk.DISABLED)
#                 self._set_status(f"Worker ID {uid} does not exist", RED, RED_DIM, RED)
#                 self._set_avatar(None, RED_DIM)
#             else:
#                 name   = worker.get("Full_Name", "N/A")
#                 status = get_worker_status(uid)
#                 self.name_lbl.config(text=name, fg=WHITE)
#                 hints = {
#                     "checked_in": ("Checked in today — use Check-Out", ORANGE),
#                     "done":        ("Attendance complete for today",    RED),
#                     "none":        ("Not yet checked in today",          TEXT2),
#                 }
#                 htxt, hcol = hints.get(status, ("", TEXT2))
#                 self.hint_lbl.config(text=htxt, fg=hcol)
#                 self._apply_status(status, name)
#         self.root.after(0, _upd)

#     def _on_enter(self, _=None):
#         uid = self.user_entry.get().strip()
#         if not uid or self._busy: return
#         s = get_worker_status(uid)
#         if s == "none":       self._trigger("checkin")
#         elif s == "checked_in": self._trigger("checkout")

#     # ── TRIGGER ─────────────────────────────────────────
#     def _trigger(self, action):
#         if self._busy: return
#         uid = self.user_entry.get().strip()
#         if not uid: return
#         self._busy = True
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         verb = "CHECK IN" if action == "checkin" else "CHECK OUT"
#         self._set_status(f"Scanning fingerprint for {verb}…", ORANGE, ORANGE_DIM, ORANGE)
#         self.root.after(0, self._scan_start)
#         threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

#     # ── MAIN WORKER THREAD ──────────────────────────────
#     def _process(self, uid, action):
#         is_open = False
#         success = False
#         msg     = ""
#         full_name = uid
#         try:
#             self.log(f"{'─'*18} {action.upper()} · ID {uid} {'─'*18}", "div")
#             if zk.GetDeviceCount() == 0:
#                 self.log("Scanner not connected", "err")
#                 self.root.after(0, lambda: self._scan_err("NO DEVICE"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Scanner Not Connected",
#                     "Connect the fingerprint device and try again.", "", "#6d28d9"))
#                 return
#             zk.OpenDevice(0); is_open = True
#             self.log("Waiting for fingerprint…", "info")
#             capture = None
#             for _ in range(150):
#                 capture = zk.AcquireFingerprint()
#                 if capture: break
#                 time.sleep(0.2)
#             if not capture:
#                 self.log("Scan timed out", "err")
#                 self.root.after(0, lambda: self._scan_err("TIMEOUT"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "⏱", "Scan Timeout", "No fingerprint detected.", "", "#92400e"))
#                 return
#             self.root.after(0, self._scan_ok)
#             self.log("Fingerprint captured ✔", "ok")
#             worker = self._worker_cache.get(uid) or find_worker(uid)
#             if worker: self._worker_cache[uid] = worker
#             if not worker:
#                 self.log(f"ID {uid} not found in Zoho", "err")
#                 self.root.after(0, lambda: self._scan_err("NOT FOUND"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Worker Not Found", f"ID {uid} does not exist.", "", RED_DIM))
#                 return
#             full_name = worker.get("Full_Name", uid)
#             self.log(f"Identity: {full_name}", "ok")
#             status = get_worker_status(uid)
#             if status == "done":
#                 self.log("Attendance already complete today", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "🔒", "Already Complete", full_name, "Done for today.", "#1e0a40"))
#                 self.root.after(2600, lambda: self._apply_status("done", full_name))
#                 return
#             if status == "checked_in" and action == "checkin":
#                 self.log("Already checked IN", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "↩", "Already Checked In", full_name, "Use Check-Out instead.", "#3d1f00"))
#                 self.root.after(2600, lambda: self._apply_status("checked_in", full_name))
#                 return
#             if status == "none" and action == "checkout":
#                 self.log("Not checked IN yet", "warn")
#                 self.root.after(0, lambda: self._show_flash(
#                     "⚠", "Not Checked In", full_name, "Check IN first.", "#1e0a40"))
#                 self.root.after(2600, lambda: self._apply_status("none", full_name))
#                 return
#             self.log(f"Posting {action.upper()} to Zoho…", "info")
#             pa  = worker.get("Projects_Assigned")
#             pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID
#             success, msg = log_attendance(worker["ID"], uid, pid, full_name, action, self.log)
#             tag = "ok" if success else "err"
#             for line in msg.splitlines():
#                 if line.strip():
#                     ltag = tag
#                     if "late" in line.lower():     ltag = "late"
#                     if "overtime" in line.lower(): ltag = "ot"
#                     if "early" in line.lower():    ltag = "early"
#                     self.log(line.strip(), ltag)
#             if success:
#                 verb      = "Checked IN" if action == "checkin" else "Checked OUT"
#                 sub       = datetime.now().strftime("Time: %H:%M:%S · %A, %d %B %Y")
#                 extra     = ""
#                 flash_col = "#1d4ed8"
#                 if action == "checkin" and is_late(datetime.now()):
#                     extra     = f"⚠ Late arrival — {late_by_str(datetime.now())}"
#                     flash_col = "#92400e"
#                 if action == "checkout":
#                     lock2 = load_lock()
#                     co    = lock2.get("checked_out", {}).get(str(uid), {})
#                     ot    = co.get("overtime_hours", 0) if isinstance(co, dict) else 0
#                     now_  = datetime.now()
#                     early_limit = now_.replace(hour=EARLY_CHECKOUT_H,
#                                                minute=EARLY_CHECKOUT_M,
#                                                second=0, microsecond=0)
#                     if now_ < early_limit:
#                         extra     = f"⚡ Early checkout — before {EARLY_CHECKOUT_H:02d}:00"
#                         flash_col = CYAN_DIM
#                     elif ot > 0:
#                         extra = f"⏱ Overtime: {int(ot)}h {int((ot%1)*60)}m"
#                 ev_tag = "in" if action == "checkin" else "out"
#                 self._add_event(verb, full_name, ev_tag)
#                 self._tick_stats()
#                 _v, _s, _e, _fc = verb, sub, extra, flash_col
#                 self.root.after(0, lambda: self._show_flash(
#                     "✔", f"{_v} — {full_name}", _s, _e, _fc))
#             else:
#                 _m = msg.splitlines()[0][:80]
#                 self.root.after(0, lambda: self._scan_err("ERROR"))
#                 self.root.after(0, lambda: self._show_flash(
#                     "✗", "Action Failed", _m, "", RED_DIM))
#         except Exception as exc:
#             self.log(f"Unexpected error: {exc}", "err")
#         finally:
#             if is_open:
#                 try: zk.CloseDevice()
#                 except: pass
#             self._busy = False
#             self.root.after(2600, self._scan_reset)
#             self.root.after(2600, lambda: self._reset_ui(clear_log=success))

#     # ── RESET ───────────────────────────────────────────
#     def _reset_ui(self, clear_log=False):
#         self.user_entry.delete(0, tk.END)
#         self.name_lbl.config(text="—", fg=MUTED)
#         self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
#         self._set_avatar(None, BORDER)
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
#         if clear_log:
#             self.log_box.config(state=tk.NORMAL)
#             self.log_box.delete("1.0", tk.END)
#             self.log_box.config(state=tk.DISABLED)
#         self.log("Ready for next worker.", "div")
#         self.user_entry.focus_set()

#     def _soft_reset(self):
#         self.name_lbl.config(text="—", fg=MUTED)
#         self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
#         self._set_avatar(None, BORDER)
#         self._set_buttons(tk.DISABLED, tk.DISABLED)
#         self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)

#     # ── CLOSE ───────────────────────────────────────────
#     def _on_close(self):
#         try: zk.Terminate()
#         except: pass
#         self.root.destroy()

# # ===========================================================
# if __name__ == "__main__":
#     root = tk.Tk()
#     FingerprintGUI(root)
#     root.mainloop()








import os, time, json, csv, requests, threading, math
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyzkfp import ZKFP2
import tkinter as tk
from tkinter import ttk, messagebox

# ===========================================================
# CONFIGURATION
# ===========================================================
load_dotenv()
ZOHO_DOMAIN      = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER        = "wavemarkpropertieslimited"
APP_NAME         = "real-estate-wages-system"
CLIENT_ID        = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET    = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN    = os.getenv("ZOHO_REFRESH_TOKEN")
WORKERS_REPORT   = "All_Workers"
ATTENDANCE_FORM  = "Daily_Attendance"
ATTENDANCE_REPORT= "Daily_Attendance_Report"
DEFAULT_PROJECT_ID = "4838902000000391493"
TOKEN_CACHE      = {"token": None, "expires_at": 0}
API_DOMAIN       = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
CHECKIN_LOCK_FILE= "checkin_today.json"

# ── Shift policy ──────────────────────────────────────────
SHIFT_START_H    = 7     # 07:00 AM
SHIFT_START_M    = 0
SHIFT_HOURS      = 8     # standard hours before overtime kicks in
GRACE_MINUTES    = 10    # 10-min grace period before "late" is flagged
EARLY_CHECKOUT_H = 17    # 5:00 PM — checkout before this = early
EARLY_CHECKOUT_M = 0

# ===========================================================
# GLOBAL SDK
# ===========================================================
zk = ZKFP2()
try:
    zk.Init()
except Exception as e:
    print(f"Fingerprint SDK Init Error: {e}")

# ===========================================================
# NETWORK & AUTHENTICATION
# ===========================================================
def zoho_request(method, url, retries=3, **kwargs):
    kwargs.setdefault("timeout", 45)
    for attempt in range(1, retries + 1):
        try:
            return requests.request(method, url, **kwargs)
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError, OSError):
            if attempt < retries:
                time.sleep(2 * attempt)
    return None

def get_access_token():
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
        return TOKEN_CACHE["token"]
    TOKEN_CACHE["token"] = None
    url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    data = {"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"}
    for _ in range(3):
        r = zoho_request("POST", url, data=data, retries=1)
        if r and r.status_code == 200:
            res = r.json()
            TOKEN_CACHE["token"]      = res.get("access_token")
            TOKEN_CACHE["expires_at"] = now + int(res.get("expires_in", 3600))
            return TOKEN_CACHE["token"]
        time.sleep(3)
    return None

def auth_headers():
    token = get_access_token()
    return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# ===========================================================
# LOCAL STATE
# ===========================================================
def load_lock():
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(CHECKIN_LOCK_FILE):
        try:
            with open(CHECKIN_LOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") == today:
                # Sanitise: ensure sub-keys are dicts of dicts
                if not isinstance(data.get("checked_in"),  dict):
                    data["checked_in"]  = {}
                if not isinstance(data.get("checked_out"), dict):
                    data["checked_out"] = {}
                # Drop any entry that isn't a dict (corrupted old-format strings)
                data["checked_in"]  = {k: v for k, v in data["checked_in"].items()
                                        if isinstance(v, dict)}
                data["checked_out"] = {k: v for k, v in data["checked_out"].items()
                                        if isinstance(v, dict)}
                return data
            # Date mismatch → new day: write a fresh file so tomorrow starts at zero
        except Exception:
            pass
    fresh = {"date": today, "checked_in": {}, "checked_out": {}}
    save_lock(fresh)
    return fresh

def save_lock(data):
    tmp = CHECKIN_LOCK_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CHECKIN_LOCK_FILE)

def get_worker_status(zk_id):
    lock = load_lock()
    key  = str(zk_id)
    if key in lock["checked_out"]:  return "done"
    if key in lock["checked_in"]:   return "checked_in"
    return "none"

def count_early_checkouts(lock=None):
    """Count workers who checked out before EARLY_CHECKOUT_H:EARLY_CHECKOUT_M."""
    if lock is None:
        lock = load_lock()
    now = datetime.now()
    early_limit = now.replace(
        hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
        second=0, microsecond=0)
    count = 0
    for info in lock.get("checked_out", {}).values():
        if not isinstance(info, dict):
            continue
        co_time_str = info.get("time", "")
        try:
            co_dt = datetime.strptime(co_time_str, "%H:%M:%S").replace(
                year=now.year, month=now.month, day=now.day)
            if co_dt < early_limit:
                count += 1
        except Exception:
            pass
    return count

# ===========================================================
# SHIFT HELPERS
# ===========================================================
def is_late(checkin_dt):
    cutoff = checkin_dt.replace(
        hour=SHIFT_START_H, minute=SHIFT_START_M,
        second=0, microsecond=0) + timedelta(minutes=GRACE_MINUTES)
    return checkin_dt > cutoff

def late_by_str(checkin_dt):
    shift_start = checkin_dt.replace(
        hour=SHIFT_START_H, minute=SHIFT_START_M, second=0, microsecond=0)
    delta = max((checkin_dt - shift_start).total_seconds(), 0)
    mins  = int(delta // 60)
    return f"{mins} min late" if mins else "on time"

def overtime_hours(total_hours):
    return max(round(total_hours - SHIFT_HOURS, 4), 0)

# ===========================================================
# ZOHO API
# ===========================================================
def find_worker(zk_user_id):
    url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
    r = zoho_request("GET", url, headers=auth_headers(), params={"criteria": criteria})
    if r and r.status_code == 200:
        data = r.json().get("data", [])
        return data[0] if data else None
    return None

def _extract_zoho_id(res_json):
    data = res_json.get("data")
    if isinstance(data, dict):
        return data.get("ID") or data.get("id")
    if isinstance(data, list) and data:
        return data[0].get("ID") or data[0].get("id")
    return res_json.get("ID") or res_json.get("id")

def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs, _log=None):
    def dbg(msg):
        print(f"[ZOHO SEARCH] {msg}")
        if _log: _log(f"[search] {msg}", "warn")
    report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
    dbg(f"worker_id={worker_id} dates={today_display}/{today_iso}")
    criteria_list = [
        f'(Worker_Name == "{worker_id}" && Date == "{today_display}")',
        f'(Worker_Name == "{worker_id}" && Date == "{today_iso}")',
        f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
        f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
        f'(Worker_Name == "{worker_id}")',
        f'(Worker_ID_Lookup == "{worker_id}")',
    ]
    for crit in criteria_list:
        r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
        if not r or r.status_code != 200:
            dbg(f"  HTTP {r.status_code if r else 'timeout'} → {crit}"); continue
        recs = r.json().get("data", [])
        dbg(f"  {len(recs)} result(s) → {crit}")
        if not recs: continue
        for rec in recs:
            d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
            if d in (today_display, today_iso):
                dbg(f"  ✔ date-matched record ID={rec['ID']}"); return rec["ID"]
        if len(recs) == 1:
            dbg(f"  ✔ single-result fallback ID={recs[0]['ID']}"); return recs[0]["ID"]
    dbg("  Trying date-only broad search...")
    for date_val in (today_display, today_iso):
        r = zoho_request("GET", report_url, headers=hdrs,
                         params={"criteria": f'(Date == "{date_val}")'})
        if not r or r.status_code != 200: continue
        recs = r.json().get("data", [])
        dbg(f"  date-only → {len(recs)} record(s) for {date_val}")
        for rec in recs:
            for field in ("Worker_Name","Worker_ID_Lookup","Worker","Worker_Name.ID","Worker_ID"):
                val = rec.get(field)
                if isinstance(val, dict):
                    val = (val.get("ID") or val.get("id") or val.get("display_value",""))
                if str(val).strip() == str(worker_id).strip():
                    dbg(f"  ✔ client-matched via '{field}' → ID={rec['ID']}"); return rec["ID"]
        if recs:
            dbg(f"  First record keys: {list(recs[0].keys())}")
            dbg(f"  First record sample: { {k: recs[0][k] for k in list(recs[0].keys())[:10]} }")
    dbg("  ✗ All strategies exhausted — record not found.")
    return None

# ===========================================================
# ATTENDANCE LOGIC
# ===========================================================
def log_attendance(worker_id, zk_id, project_id, full_name, action, _log=None):
    now       = datetime.now()
    zk_key    = str(zk_id)
    today_display = now.strftime("%d-%b-%Y")
    today_iso     = now.strftime("%Y-%m-%d")

    if action == "checkin":
        form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
        checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
        hdrs         = auth_headers()
        worker_late  = is_late(now)
        late_note    = late_by_str(now)
        payload = {"data": {
            "Worker_Name": worker_id, "Projects": project_id,
            "Date": today_display, "First_In": checkin_time,
            "Worker_Full_Name": full_name,
            "Is_Late": "true" if worker_late else "false",
            "Late_By_Minutes": int(max((now - now.replace(
                hour=SHIFT_START_H, minute=SHIFT_START_M,
                second=0, microsecond=0)).total_seconds() // 60, 0)) if worker_late else 0,
        }}
        r = zoho_request("POST", form_url, headers=hdrs, json=payload)
        if r and r.status_code in (200, 201):
            res          = r.json()
            zoho_rec_id  = _extract_zoho_id(res)
            if not zoho_rec_id:
                zoho_rec_id = _find_record_in_zoho(
                    worker_id, today_display, today_iso, auth_headers(), _log)
            lock = load_lock()
            lock["checked_in"][zk_key] = {
                "time": checkin_time, "zoho_id": zoho_rec_id,
                "worker_id": worker_id, "name": full_name,
                "is_late": worker_late, "late_note": late_note,
            }
            save_lock(lock)
            status_line = f"⚠ {late_note}" if worker_late else "✓ On time"
            return True, (
                f"✅ {full_name} checked IN at {now.strftime('%H:%M')}\n"
                f"   {status_line}")
        err = r.text[:200] if r else "Timeout"
        return False, f"Check-in failed: {err}"

    elif action == "checkout":
        lock = load_lock()
        info = lock["checked_in"].get(zk_key)
        if not info:
            return False, "No check-in record found for today."
        hdrs = auth_headers()
        if not hdrs:
            return False, "Could not refresh Zoho token — check internet."
        att_record_id  = info.get("zoho_id")
        stored_worker  = info.get("worker_id", worker_id)

        def dbg(msg):
            print(f"[CHECKOUT] {msg}")
            if _log: _log(f"[checkout] {msg}", "warn")

        dbg(f"stored zoho_id={att_record_id} stored_worker={stored_worker}")

        if att_record_id:
            direct_url = (f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
                          f"/report/{ATTENDANCE_REPORT}/{att_record_id}")
            r_chk = zoho_request("GET", direct_url, headers=hdrs)
            dbg(f"direct GET by ID → HTTP {r_chk.status_code if r_chk else 'timeout'}")
            if r_chk and r_chk.status_code == 200:
                dbg("stored ID confirmed valid ✔")
            else:
                dbg("stored ID invalid — clearing and searching...")
                att_record_id = None

        if not att_record_id:
            att_record_id = _find_record_in_zoho(
                stored_worker, today_display, today_iso, hdrs, _log)
            if att_record_id:
                lock["checked_in"][zk_key]["zoho_id"] = att_record_id
                save_lock(lock)

        if not att_record_id:
            report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
            r_all = zoho_request("GET", report_url, headers=hdrs,
                                 params={"from": 1, "limit": 5})
            if r_all and r_all.status_code == 200:
                all_recs = r_all.json().get("data", [])
                dbg(f"no-criteria probe → {len(all_recs)} record(s) in report")
                for i, rec in enumerate(all_recs):
                    dbg(f"  rec[{i}] keys={list(rec.keys())}")
                    dbg(f"  rec[{i}] sample={ {k: rec[k] for k in list(rec.keys())[:8]} }")

        form_index_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
        for date_val in (today_display, today_iso):
            crit = f'(Worker_Name == "{stored_worker}" && Date == "{date_val}")'
            r_f  = zoho_request("GET", form_index_url, headers=hdrs, params={"criteria": crit})
            dbg(f"form GET ({date_val}) → HTTP {r_f.status_code if r_f else 'timeout'}")
            if r_f and r_f.status_code == 200:
                frecs = r_f.json().get("data", [])
                dbg(f"  form returned {len(frecs)} record(s)")
                if frecs:
                    att_record_id = frecs[0].get("ID")
                    dbg(f"  ✔ found via form endpoint → ID={att_record_id}")
                    lock["checked_in"][zk_key]["zoho_id"] = att_record_id
                    save_lock(lock)
                    break

        if not att_record_id:
            return False, (
                f"Could not locate today's attendance record in Zoho.\n"
                f"Worker: {full_name} Date: {today_display}\n"
                f"Stored Zoho ID: {info.get('zoho_id', 'None')}\n"
                "Check the terminal/log for [checkout] diagnostics.\n"
                "The record may not have been created at check-in time.")

        try:
            dt_in = datetime.strptime(info.get("time", ""), "%d-%b-%Y %H:%M:%S")
        except Exception:
            dt_in = now
        total_hours       = max((now - dt_in).total_seconds() / 3600, 0.01)
        ot_hours          = overtime_hours(total_hours)
        total_str         = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"
        ot_str            = f"{int(ot_hours)}h {int((ot_hours % 1) * 60)}m" if ot_hours else "None"
        total_hours_rounded = round(total_hours, 2)
        ot_hours_rounded    = round(ot_hours, 2)
        dbg(f"hours: total={total_hours_rounded} overtime={ot_hours_rounded}")

        update_url = (f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
                      f"/report/{ATTENDANCE_REPORT}/{att_record_id}")
        dbg(f"PATCH → {ATTENDANCE_REPORT}/{att_record_id}")
        r_u = zoho_request("PATCH", update_url, headers=hdrs, json={"data": {
            "Last_Out": now.strftime("%d-%b-%Y %H:%M:%S"),
            "Total_Hours": total_hours_rounded,
            "Overtime_Hours": ot_hours_rounded,
        }})
        http_code = r_u.status_code if r_u else "timeout"
        body_raw  = r_u.text[:300] if r_u else "No response"
        dbg(f"PATCH result → HTTP {http_code} body={body_raw}")

        if r_u and r_u.status_code == 200:
            body = r_u.json()
            code = body.get("code")
            if code == 3000:
                checkout_time_str = now.strftime("%H:%M:%S")
                lock["checked_in"].pop(zk_key, None)
                lock["checked_out"][zk_key] = {
                    "time": checkout_time_str,
                    "name": full_name,
                    "total_hours": total_hours_rounded,
                    "overtime_hours": ot_hours_rounded,
                    "is_late": info.get("is_late", False),
                    "late_note": info.get("late_note", ""),
                    "checkin_time": info.get("time", ""),
                }
                save_lock(lock)
                ot_line = f"   Overtime: {ot_str}" if ot_hours else ""
                # Check if early checkout
                early_limit = now.replace(
                    hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
                    second=0, microsecond=0)
                early_note = ""
                if now < early_limit:
                    early_note = (f"\n   ⚠ Early checkout "
                                  f"(before {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d})")
                return True, (
                    f"🚪 {full_name} checked OUT at {now.strftime('%H:%M')}\n"
                    f"   Total time: {total_str}\n"
                    f"{ot_line}{early_note}")
            errors = body.get("error", body.get("message", ""))
            return False, (
                f"Zoho rejected the update (code {code}).\n"
                f"Error: {errors}\n"
                f"Worker: {full_name} Hours sent: {total_hours_rounded}")
        return False, f"Check-out PATCH failed (HTTP {http_code}): {body_raw}"
    return False, "Unknown action."

# ===========================================================
# DAILY SUMMARY EXPORT
# ===========================================================
def export_daily_summary():
    lock     = load_lock()
    today    = lock.get("date", datetime.now().strftime("%Y-%m-%d"))
    filename = f"attendance_{today}.csv"
    rows     = []
    early_limit = datetime.now().replace(
        hour=EARLY_CHECKOUT_H, minute=EARLY_CHECKOUT_M,
        second=0, microsecond=0)

    for zk_id, info in lock.get("checked_out", {}).items():
        co_str = info.get("time", "")
        is_early = False
        try:
            co_dt = datetime.strptime(co_str, "%H:%M:%S").replace(
                year=datetime.now().year, month=datetime.now().month,
                day=datetime.now().day)
            is_early = co_dt < early_limit
        except Exception:
            pass
        rows.append({
            "ZK_ID": zk_id, "Name": info.get("name",""),
            "Check-In": info.get("checkin_time",""), "Check-Out": co_str,
            "Total Hours": info.get("total_hours",""),
            "Overtime Hours": info.get("overtime_hours", 0),
            "Late?": "Yes" if info.get("is_late") else "No",
            "Late Note": info.get("late_note",""),
            "Early Checkout?": "Yes" if is_early else "No",
            "Status": "Complete",
        })
    for zk_id, info in lock.get("checked_in", {}).items():
        rows.append({
            "ZK_ID": zk_id, "Name": info.get("name",""),
            "Check-In": info.get("time",""), "Check-Out": "—",
            "Total Hours": "—", "Overtime Hours": "—",
            "Late?": "Yes" if info.get("is_late") else "No",
            "Late Note": info.get("late_note",""),
            "Early Checkout?": "—", "Status": "Still In",
        })
    if not rows: return None
    fieldnames = ["ZK_ID","Name","Check-In","Check-Out","Total Hours",
                  "Overtime Hours","Late?","Late Note","Early Checkout?","Status"]
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return filename

# ===========================================================
# COLOUR PALETTE
# ===========================================================
BG          = "#07090f"
CARD        = "#0c1018"
CARD2       = "#10151f"
CARD3       = "#141b27"
BORDER      = "#1c2438"
BORDER2     = "#243048"
ACCENT      = "#3b82f6"
ACCENT_DIM  = "#172554"
ACCENT2     = "#60a5fa"
GREEN       = "#10b981"
GREEN2      = "#34d399"
GREEN_DIM   = "#052e1c"
RED         = "#f43f5e"
RED2        = "#fb7185"
RED_DIM     = "#4c0519"
ORANGE      = "#f59e0b"
ORANGE2     = "#fbbf24"
ORANGE_DIM  = "#3d1f00"
CYAN        = "#06b6d4"
CYAN2       = "#67e8f9"
CYAN_DIM    = "#083344"
TEXT        = "#e2e8f0"
TEXT2       = "#94a3b8"
MUTED       = "#3d4f69"
WHITE       = "#ffffff"
GOLD        = "#f59e0b"
GOLD2       = "#fde68a"
PURPLE      = "#a78bfa"
PURPLE_DIM  = "#2e1065"

# ===========================================================
# SHARED UI HELPERS
# ===========================================================
def _btn_hover(btn, bg_on, fg_on, bg_off, fg_off):
    btn.bind("<Enter>",  lambda _: btn.config(bg=bg_on,  fg=fg_on))
    btn.bind("<Leave>",  lambda _: btn.config(bg=bg_off, fg=fg_off))

def _make_sep(parent, color=BORDER, height=1):
    tk.Frame(parent, bg=color, height=height).pack(fill=tk.X)

def _initials(name):
    parts = name.strip().split()
    if not parts:      return "??"
    if len(parts) == 1: return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

# ===========================================================
# FINGERPRINT CANVAS WIDGET
# ===========================================================
class FingerprintCanvas(tk.Canvas):
    """
    Animated fingerprint visual — concentric arcs that rotate
    when scanning, pulse green on success, flash red on error.
    """
    SIZE = 140

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=CARD2, highlightthickness=0, **kwargs)
        self._cx = self._cy = self.SIZE // 2
        self._angle  = 0
        self._active = False
        self._state  = "idle"   # idle | scanning | ok | error
        self._phase  = 0
        self._items  = []
        self._draw_base()
        self._animate()

    def _draw_base(self):
        """Draw the static fingerprint-like concentric arc skeleton."""
        cx, cy = self._cx, self._cy
        self.delete("fp")
        # Outer glow ring
        self.create_oval(cx-64, cy-64, cx+64, cy+64,
                         outline=BORDER2, width=1, tags="fp")
        # Fingerprint arcs — alternating open arcs to mimic ridge lines
        arc_defs = [
            (10, 0,   300, 2),
            (18, 20,  280, 2),
            (26, 30,  270, 1),
            (34, 15,  290, 1),
            (42, 25,  265, 1),
            (50, 10,  285, 1),
            (58, 35,  250, 1),
        ]
        self._arc_items = []
        for r, start, extent, w in arc_defs:
            item = self.create_arc(
                cx-r, cy-r, cx+r, cy+r,
                start=start, extent=extent,
                outline=MUTED, width=w, style="arc", tags="fp")
            self._arc_items.append(item)
        # Centre dot
        self._centre = self.create_oval(
            cx-5, cy-5, cx+5, cy+5,
            fill=MUTED, outline="", tags="fp")
        # Spinning scan arc (hidden by default)
        self._spin = self.create_arc(
            cx-58, cy-58, cx+58, cy+58,
            start=0, extent=0,
            outline=ACCENT, width=3, style="arc", tags="fp")

    def start(self):
        self._state  = "scanning"
        self._active = True

    def stop_ok(self):
        self._state  = "ok"
        self._active = False
        self._flash_ok()

    def stop_err(self, msg="ERROR"):
        self._state  = "error"
        self._active = False
        self._flash_err()

    def reset(self):
        self._state  = "idle"
        self._active = False
        self._angle  = 0
        self._draw_base()

    def _flash_ok(self):
        cx, cy = self._cx, self._cy
        for item in self._arc_items:
            self.itemconfig(item, outline=GREEN2)
        self.itemconfig(self._centre, fill=GREEN2)
        self.itemconfig(self._spin, extent=0)

    def _flash_err(self):
        cx, cy = self._cx, self._cy
        for item in self._arc_items:
            self.itemconfig(item, outline=RED2)
        self.itemconfig(self._centre, fill=RED2)
        self.itemconfig(self._spin, extent=0)

    def _animate(self):
        self._phase = (self._phase + 1) % 120
        cx, cy = self._cx, self._cy

        if self._state == "scanning":
            self._angle = (self._angle + 6) % 360
            # Sweep arc
            sweep = int(200 * abs(math.sin(math.radians(self._angle))))
            self.itemconfig(self._spin,
                            start=self._angle, extent=sweep,
                            outline=ACCENT)
            # Pulse arcs
            alpha = 0.4 + 0.6 * abs(math.sin(math.radians(self._phase * 3)))
            r_val = int(int(ACCENT[1:3], 16) * alpha)
            g_val = int(int(ACCENT[3:5], 16) * alpha)
            b_val = int(int(ACCENT[5:7], 16) * alpha)
            col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            for i, item in enumerate(self._arc_items):
                phase_offset = self._phase + i * 10
                a2 = 0.3 + 0.7 * abs(math.sin(math.radians(phase_offset * 4)))
                r2 = int(int(ACCENT[1:3], 16) * a2)
                g2 = int(int(ACCENT[3:5], 16) * a2)
                b2 = int(int(ACCENT[5:7], 16) * a2)
                self.itemconfig(item, outline=f"#{r2:02x}{g2:02x}{b2:02x}")
            self.itemconfig(self._centre, fill=col)

        elif self._state == "ok":
            # Gentle pulse green
            alpha = 0.6 + 0.4 * abs(math.sin(math.radians(self._phase * 2)))
            r_val = int(int(GREEN2[1:3], 16) * alpha)
            g_val = int(int(GREEN2[3:5], 16) * alpha)
            b_val = int(int(GREEN2[5:7], 16) * alpha)
            col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            for item in self._arc_items:
                self.itemconfig(item, outline=col)
            self.itemconfig(self._centre, fill=col)

        elif self._state == "error":
            # Flash red
            alpha = 0.4 + 0.6 * abs(math.sin(math.radians(self._phase * 6)))
            r_val = int(int(RED2[1:3], 16) * alpha)
            g_val = int(int(RED2[3:5], 16) * alpha)
            b_val = int(int(RED2[5:7], 16) * alpha)
            col = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
            for item in self._arc_items:
                self.itemconfig(item, outline=col)
            self.itemconfig(self._centre, fill=col)

        else:  # idle — slow breath
            alpha = 0.25 + 0.20 * abs(math.sin(math.radians(self._phase * 1.5)))
            r_val = int(int(MUTED[1:3], 16) * alpha * 2.5)
            g_val = int(int(MUTED[3:5], 16) * alpha * 2.5)
            b_val = int(int(MUTED[5:7], 16) * alpha * 2.5)
            col = f"#{min(r_val,255):02x}{min(g_val,255):02x}{min(b_val,255):02x}"
            for item in self._arc_items:
                self.itemconfig(item, outline=col)
            self.itemconfig(self._spin, extent=0)

        self.after(30, self._animate)

# ===========================================================
# PULSING LED
# ===========================================================
class PulseLED(tk.Canvas):
    SIZE = 12
    def __init__(self, parent, color=ACCENT):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=parent.cget("bg"), highlightthickness=0)
        r = self.SIZE // 2
        self._dot   = self.create_oval(2, 2, r*2-2, r*2-2, fill=color, outline="")
        self._color = color
        self._phase = 0
        self._pulse()

    def set_color(self, color):
        self._color = color
        self.itemconfig(self._dot, fill=color)

    def _pulse(self):
        self._phase = (self._phase + 1) % 60
        alpha = 0.55 + 0.45 * abs((self._phase % 60) - 30) / 30
        c = self._color
        try:
            r = int(int(c[1:3], 16) * alpha)
            g = int(int(c[3:5], 16) * alpha)
            b = int(int(c[5:7], 16) * alpha)
            self.itemconfig(self._dot, fill=f"#{r:02x}{g:02x}{b:02x}")
        except Exception:
            pass
        self.after(50, self._pulse)

# ===========================================================
# DASHBOARD KPI RING (donut chart on canvas)
# ===========================================================
class DonutRing(tk.Canvas):
    """Mini donut chart showing checked-in vs checked-out ratio."""
    SIZE = 80

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=CARD2, highlightthickness=0, **kwargs)
        self._val = 0   # 0..1 fill
        self._phase = 0
        self._color = GREEN2
        self._draw(0)
        self._tick()

    def set_value(self, fraction, color=GREEN2):
        self._val   = max(0.0, min(1.0, fraction))
        self._color = color
        self._draw(self._val)

    def _draw(self, fraction):
        self.delete("all")
        cx = cy = self.SIZE // 2
        r  = cx - 6
        # Background ring
        self.create_arc(cx-r, cy-r, cx+r, cy+r,
                        start=0, extent=359.9,
                        outline=BORDER2, width=10, style="arc")
        # Value arc
        if fraction > 0:
            ext = fraction * 359.9
            alpha = 0.7 + 0.3 * abs(math.sin(math.radians(self._phase * 2)))
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=90, extent=-ext,
                            outline=self._color, width=10, style="arc")
        # Centre text
        pct = int(fraction * 100)
        self.create_text(cx, cy, text=f"{pct}%",
                         font=("Courier", 11, "bold"),
                         fill=self._color if fraction > 0 else MUTED)

    def _tick(self):
        self._phase += 1
        self._draw(self._val)
        self.after(100, self._tick)

# ===========================================================
# ADMIN PANEL
# ===========================================================
class AdminPanel(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Attendance Command Center")
        self.configure(bg=BG)
        self.resizable(True, True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        W, H   = min(sw, 1150), min(sh, 700)
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self._build()
        self.refresh()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg=PURPLE, height=2).pack(fill=tk.X)
        hi = tk.Frame(hdr, bg=CARD, padx=24, pady=14)
        hi.pack(fill=tk.X)
        lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
        tk.Label(lf, text="ATTENDANCE COMMAND CENTER",
                 font=("Courier", 13, "bold"), bg=CARD, fg=PURPLE).pack(anchor="w")
        self.sub_lbl = tk.Label(lf, text="", font=("Courier", 8), bg=CARD, fg=TEXT2)
        self.sub_lbl.pack(anchor="w", pady=(2, 0))
        rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
        for txt, cmd, bg_, fg_ in [
            ("↻ REFRESH", self.refresh, ACCENT_DIM, ACCENT2),
            ("⬇ EXPORT CSV", self._export, GREEN_DIM, GREEN2),
            ("✕ CLOSE", self.destroy, BORDER, TEXT2),
        ]:
            b = tk.Button(rf, text=txt, font=("Courier", 9, "bold"),
                          relief=tk.FLAT, bg=bg_, fg=fg_, cursor="hand2",
                          padx=14, pady=6, command=cmd)
            b.pack(side=tk.LEFT, padx=(0, 6))

        # KPI tiles
        self.kpi_fr = tk.Frame(self, bg=BG, padx=20, pady=12)
        self.kpi_fr.pack(fill=tk.X)

        _make_sep(self, BORDER2)

        # Table
        tree_wrap = tk.Frame(self, bg=BG, padx=20, pady=12)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Cmd.Treeview", background=CARD2, foreground=TEXT,
                         fieldbackground=CARD2, rowheight=30,
                         font=("Courier", 9), borderwidth=0)
        style.configure("Cmd.Treeview.Heading", background=CARD,
                         foreground=GOLD, font=("Courier", 9, "bold"),
                         relief="flat", borderwidth=0)
        style.map("Cmd.Treeview",
                  background=[("selected", ACCENT_DIM)],
                  foreground=[("selected", ACCENT2)])
        cols    = ("Initials","Name","Check-In","Check-Out","Hours","Overtime","Early Out?","Late","Status")
        widths  = (60, 190, 110, 110, 80, 90, 90, 80, 90)
        anchors = ("center","w","center","center","center","center","center","center","center")
        self.tree = ttk.Treeview(tree_wrap, columns=cols,
                                 show="headings", style="Cmd.Treeview",
                                 selectmode="browse")
        for col, w, a in zip(cols, widths, anchors):
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=w, anchor=a, stretch=(col == "Name"))
        self.tree.tag_configure("late",     foreground=ORANGE2)
        self.tree.tag_configure("ot",       foreground=PURPLE)
        self.tree.tag_configure("complete", foreground=GREEN2)
        self.tree.tag_configure("still_in", foreground=ACCENT2)
        self.tree.tag_configure("early",    foreground=CYAN2)
        self.tree.tag_configure("alt",      background="#0e1320")
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        lock        = load_lock()
        checked_in  = lock.get("checked_in",  {})
        checked_out = lock.get("checked_out", {})
        total       = len(checked_in) + len(checked_out)
        late_count  = ot_count = early_count = 0
        now         = datetime.now()
        early_limit = now.replace(hour=EARLY_CHECKOUT_H,
                                  minute=EARLY_CHECKOUT_M,
                                  second=0, microsecond=0)
        row_idx = 0

        def _insert(values, tags):
            nonlocal row_idx
            if row_idx % 2 == 1:
                tags = list(tags) + ["alt"]
            self.tree.insert("", tk.END, values=values, tags=tuple(tags))
            row_idx += 1

        for zk_id, info in sorted(checked_out.items(),
                                   key=lambda x: x[1].get("checkin_time", "")):
            name    = info.get("name", zk_id)
            ci      = info.get("checkin_time", "—")
            ci_s    = ci[-8:] if len(ci) > 8 else ci
            co      = info.get("time", "—")
            hrs     = info.get("total_hours", 0)
            ot      = info.get("overtime_hours", 0)
            late    = info.get("is_late", False)
            h_str   = f"{int(hrs)}h {int((hrs%1)*60):02d}m" if isinstance(hrs,(int,float)) else str(hrs)
            o_str   = f"{int(ot)}h {int((ot%1)*60):02d}m" if ot else "—"
            # Early checkout?
            is_early = False
            try:
                co_dt = datetime.strptime(co, "%H:%M:%S").replace(
                    year=now.year, month=now.month, day=now.day)
                is_early = co_dt < early_limit
            except Exception:
                pass
            if late:    late_count  += 1
            if ot > 0:  ot_count    += 1
            if is_early: early_count += 1
            tags = []
            if late:     tags.append("late")
            if ot > 0:   tags.append("ot")
            if is_early: tags.append("early")
            tags.append("complete")
            _insert((_initials(name), name, ci_s, co, h_str, o_str,
                     "⚡ EARLY" if is_early else "—",
                     "⚠ LATE" if late else "—", "✔ DONE"), tags)

        for zk_id, info in sorted(checked_in.items(),
                                   key=lambda x: x[1].get("time", "")):
            name = info.get("name", zk_id)
            ci   = info.get("time", "—")
            late = info.get("is_late", False)
            try:
                dt_in   = datetime.strptime(ci, "%d-%b-%Y %H:%M:%S")
                elapsed = (now - dt_in).total_seconds() / 3600
                h_str   = f"{int(elapsed)}h {int((elapsed%1)*60):02d}m"
            except Exception:
                h_str = "—"
            ci_s = ci[-8:] if len(ci) > 8 else ci
            if late: late_count += 1
            tags = ["late"] if late else []
            tags.append("still_in")
            _insert((_initials(name), name, ci_s, "—", h_str, "—", "—",
                     "⚠ LATE" if late else "—", "● ACTIVE"), tags)

        # KPI tiles
        for w in self.kpi_fr.winfo_children():
            w.destroy()
        kpis = [
            ("TOTAL TODAY",      total,              WHITE,   BORDER2),
            ("CHECKED IN",       len(checked_in) + len(checked_out), ACCENT2, "#0d1f3f"),
            ("CHECKED OUT",      len(checked_out),   GREEN2,  "#0a3321"),
            ("EARLY CHECKOUT",   early_count,         CYAN2,   CYAN_DIM),
            ("LATE ARRIVALS",    late_count,           ORANGE2, "#3d1f00"),
            ("OVERTIME",         ot_count,             PURPLE,  "#1e0a40"),
        ]
        for label, val, fg, border_col in kpis:
            tile = tk.Frame(self.kpi_fr, bg=CARD2, padx=18, pady=10,
                            highlightbackground=border_col, highlightthickness=1)
            tile.pack(side=tk.LEFT, padx=(0, 10), fill=tk.Y)
            tk.Label(tile, text=str(val), font=("Courier", 26, "bold"),
                     bg=CARD2, fg=fg).pack()
            tk.Label(tile, text=label, font=("Courier", 7, "bold"),
                     bg=CARD2, fg=TEXT2).pack()
        self.sub_lbl.config(
            text=(f"Date: {lock.get('date','')}  "
                  f"Shift: {SHIFT_START_H:02d}:{SHIFT_START_M:02d}  "
                  f"Standard: {SHIFT_HOURS}h  "
                  f"Grace: {GRACE_MINUTES}min  "
                  f"Early Out before: {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d}  "
                  f"Refreshed: {now.strftime('%H:%M:%S')}"))

    def _export(self):
        fname = export_daily_summary()
        if fname:
            messagebox.showinfo("Export Complete",
                                f"Saved to:\n{os.path.abspath(fname)}", parent=self)
        else:
            messagebox.showwarning("Nothing to Export",
                                   "No attendance records for today.", parent=self)

# ===========================================================
# MAIN GUI
# ===========================================================
class FingerprintGUI:
    def __init__(self, root):
        self.root        = root
        self.root.title("Wavemark Properties — Attendance Terminal")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._busy          = False
        self._debounce_job  = None
        self._worker_cache  = {}
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        W, H   = min(sw, 980), min(sh, 800)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self._build_ui()
        self._tick_clock()
        self._tick_stats()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── BUILD ────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_body()
        self._build_footer()
        self._build_flash()

    # ── HEADER ──────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=CARD)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)
        hi = tk.Frame(hdr, bg=CARD, padx=28, pady=14)
        hi.pack(fill=tk.X)
        lf = tk.Frame(hi, bg=CARD); lf.pack(side=tk.LEFT)
        tk.Label(lf, text="WAVEMARK PROPERTIES LIMITED",
                 font=("Courier", 11, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
        tk.Label(lf, text="Biometric Attendance Terminal · v4.0",
                 font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(1, 0))
        rf = tk.Frame(hi, bg=CARD); rf.pack(side=tk.RIGHT)
        btn_admin = tk.Button(rf, text="⚙ ADMIN PANEL",
                              font=("Courier", 8, "bold"), relief=tk.FLAT,
                              bg=PURPLE_DIM, fg=PURPLE,
                              activebackground=PURPLE, activeforeground=WHITE,
                              cursor="hand2", padx=10, pady=5,
                              command=self._open_admin)
        btn_admin.pack(anchor="e", pady=(0, 6))
        _btn_hover(btn_admin, PURPLE, WHITE, PURPLE_DIM, PURPLE)
        self.date_lbl  = tk.Label(rf, text="", font=("Courier", 8),  bg=CARD, fg=TEXT2)
        self.date_lbl.pack(anchor="e")
        self.clock_lbl = tk.Label(rf, text="", font=("Courier", 24, "bold"), bg=CARD, fg=WHITE)
        self.clock_lbl.pack(anchor="e")
        _make_sep(self.root, BORDER2)
        sbar = tk.Frame(self.root, bg=CARD2, padx=28, pady=6)
        sbar.pack(fill=tk.X)
        shift_txt = (f"SHIFT {SHIFT_START_H:02d}:{SHIFT_START_M:02d} · "
                     f"STANDARD {SHIFT_HOURS}H · "
                     f"GRACE {GRACE_MINUTES}MIN · "
                     f"EARLY CHECKOUT BEFORE {EARLY_CHECKOUT_H:02d}:{EARLY_CHECKOUT_M:02d}")
        tk.Label(sbar, text=shift_txt, font=("Courier", 8), bg=CARD2, fg=MUTED).pack(side=tk.LEFT)
        tk.Label(sbar, text="ENTER → auto-action   ESC → clear",
                 font=("Courier", 8), bg=CARD2, fg=MUTED).pack(side=tk.RIGHT)

    # ── BODY ────────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self.root, bg=BG, padx=24, pady=14)
        body.pack(fill=tk.BOTH, expand=True)
        cols = tk.Frame(body, bg=BG)
        cols.pack(fill=tk.BOTH, expand=True)
        left  = tk.Frame(cols, bg=BG); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsep  = tk.Frame(cols, bg=BORDER, width=1); vsep.pack(side=tk.LEFT, fill=tk.Y, padx=16)
        right = tk.Frame(cols, bg=BG, width=300); right.pack(side=tk.LEFT, fill=tk.Y)
        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        # ── Worker ID card ────────────────────────────
        id_card = tk.Frame(parent, bg=CARD2,
                           highlightbackground=BORDER2, highlightthickness=1)
        id_card.pack(fill=tk.X, pady=(0, 12))
        ch = tk.Frame(id_card, bg=CARD, padx=18, pady=10); ch.pack(fill=tk.X)
        tk.Label(ch, text="WORKER IDENTIFICATION",
                 font=("Courier", 8, "bold"), bg=CARD, fg=TEXT2).pack(side=tk.LEFT)
        self._led = PulseLED(ch, MUTED); self._led.pack(side=tk.RIGHT, padx=(0, 2))
        _make_sep(id_card, BORDER)
        ci = tk.Frame(id_card, bg=CARD2, padx=18, pady=14); ci.pack(fill=tk.X)
        er = tk.Frame(ci, bg=CARD2); er.pack(fill=tk.X)
        tk.Label(er, text="ID", font=("Courier", 8, "bold"),
                 bg=CARD2, fg=MUTED, width=3, anchor="w").pack(side=tk.LEFT)
        eb = tk.Frame(er, bg=GOLD, padx=1, pady=1); eb.pack(side=tk.LEFT, padx=(6, 0))
        ei = tk.Frame(eb, bg="#09101a"); ei.pack()
        self.user_entry = tk.Entry(ei, font=("Courier", 28, "bold"), width=9,
                                   bd=0, bg="#09101a", fg=WHITE,
                                   insertbackground=GOLD,
                                   selectbackground=GOLD2, selectforeground=BG)
        self.user_entry.pack(padx=14, pady=8)
        self.user_entry.bind("<KeyRelease>",  self._on_key)
        self.user_entry.bind("<Return>",      self._on_enter)
        self.user_entry.bind("<Escape>",      lambda _: self._reset_ui())
        self.user_entry.focus_set()
        btn_clr = tk.Button(er, text="✕", font=("Courier", 10, "bold"),
                            relief=tk.FLAT, bg=BORDER, fg=MUTED,
                            activebackground=RED_DIM, activeforeground=RED,
                            cursor="hand2", padx=8, pady=4, command=self._reset_ui)
        btn_clr.pack(side=tk.LEFT, padx=(10, 0))
        _btn_hover(btn_clr, RED_DIM, RED, BORDER, MUTED)
        # Identity row
        idf = tk.Frame(ci, bg=CARD2); idf.pack(fill=tk.X, pady=(12, 0))
        self._avatar_cv = tk.Canvas(idf, width=48, height=48, bg=CARD2, highlightthickness=0)
        self._avatar_cv.pack(side=tk.LEFT, padx=(0, 12))
        self._avatar_circle = self._avatar_cv.create_oval(2,2,46,46, fill=BORDER, outline="")
        self._avatar_text   = self._avatar_cv.create_text(24,24, text="",
                                                           font=("Courier", 13, "bold"),
                                                           fill=MUTED)
        info_col = tk.Frame(idf, bg=CARD2); info_col.pack(side=tk.LEFT, fill=tk.X)
        self.name_lbl = tk.Label(info_col, text="—",
                                  font=("Courier", 16, "bold"), bg=CARD2, fg=MUTED)
        self.name_lbl.pack(anchor="w")
        self.hint_lbl = tk.Label(info_col, text="Enter a Worker ID above",
                                  font=("Courier", 9), bg=CARD2, fg=MUTED)
        self.hint_lbl.pack(anchor="w", pady=(2, 0))

        # ── Status banner ─────────────────────────────
        self.sf = tk.Frame(parent, bg=ACCENT_DIM,
                           highlightbackground=ACCENT, highlightthickness=1)
        self.sf.pack(fill=tk.X, pady=(0, 12))
        sb_inner = tk.Frame(self.sf, bg=ACCENT_DIM); sb_inner.pack(fill=tk.X, padx=16, pady=10)
        self._status_led = PulseLED(sb_inner, ACCENT); self._status_led.pack(side=tk.LEFT, padx=(0,8))
        self.sl = tk.Label(sb_inner, text="Awaiting Worker ID",
                           font=("Courier", 10, "bold"), bg=ACCENT_DIM, fg=ACCENT, anchor="w")
        self.sl.pack(side=tk.LEFT, fill=tk.X)

        # ── Action buttons ────────────────────────────
        br = tk.Frame(parent, bg=BG); br.pack(fill=tk.X, pady=(0, 12))
        self.btn_in = tk.Button(br, text="▶ CHECK IN",
                                font=("Courier", 12, "bold"), width=15, relief=tk.FLAT,
                                bg=GREEN_DIM, fg=MUTED,
                                activebackground=GREEN, activeforeground=BG,
                                cursor="hand2", state=tk.DISABLED,
                                command=lambda: self._trigger("checkin"))
        self.btn_in.pack(side=tk.LEFT, ipady=12, padx=(0, 10))
        self.btn_out = tk.Button(br, text="◼ CHECK OUT",
                                 font=("Courier", 12, "bold"), width=15, relief=tk.FLAT,
                                 bg=RED_DIM, fg=MUTED,
                                 activebackground=RED, activeforeground=WHITE,
                                 cursor="hand2", state=tk.DISABLED,
                                 command=lambda: self._trigger("checkout"))
        self.btn_out.pack(side=tk.LEFT, ipady=12, padx=(0, 10))
        btn_exp = tk.Button(br, text="⬇", font=("Courier", 11, "bold"),
                            relief=tk.FLAT, bg=BORDER, fg=TEXT2,
                            cursor="hand2", padx=12, command=self._quick_export)
        btn_exp.pack(side=tk.RIGHT, ipady=12)
        _btn_hover(btn_exp, GREEN_DIM, GREEN2, BORDER, TEXT2)

        _make_sep(parent, BORDER, height=1)
        tk.Frame(parent, bg=BG, height=8).pack()

        # ── Activity log ──────────────────────────────
        lh = tk.Frame(parent, bg=BG); lh.pack(fill=tk.X, pady=(0, 6))
        tk.Label(lh, text="ACTIVITY LOG", font=("Courier", 8, "bold"),
                 bg=BG, fg=MUTED).pack(side=tk.LEFT)
        btn_clrlog = tk.Button(lh, text="CLEAR", font=("Courier", 7, "bold"),
                               relief=tk.FLAT, bg=BORDER, fg=MUTED,
                               padx=8, pady=2, cursor="hand2", command=self._clear_log)
        btn_clrlog.pack(side=tk.RIGHT)
        _btn_hover(btn_clrlog, BORDER2, TEXT2, BORDER, MUTED)
        lw = tk.Frame(parent, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        lw.pack(fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box = tk.Text(lw, font=("Courier", 9), bg=CARD, fg=TEXT2,
                               relief=tk.FLAT, padx=14, pady=10,
                               yscrollcommand=sb.set, state=tk.DISABLED, cursor="arrow")
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.log_box.yview)
        for tag, col in [("ok", GREEN2), ("err", RED2), ("warn", ORANGE2),
                          ("info", ACCENT2), ("ts", MUTED), ("div", BORDER2),
                          ("late", ORANGE), ("ot", PURPLE), ("early", CYAN2)]:
            self.log_box.tag_config(tag, foreground=col)

    def _build_right(self, parent):
        """Right panel: fingerprint + live dashboard."""
        # ── Fingerprint visual ────────────────────────
        fp_lbl = tk.Label(parent, text="BIOMETRIC SCANNER",
                          font=("Courier", 8, "bold"), bg=BG, fg=MUTED)
        fp_lbl.pack(anchor="w", pady=(0, 8))
        sc = tk.Frame(parent, bg=CARD2,
                      highlightbackground=BORDER2, highlightthickness=1)
        sc.pack(fill=tk.X, pady=(0, 14))
        sc_inner = tk.Frame(sc, bg=CARD2, pady=16); sc_inner.pack()
        self._fp = FingerprintCanvas(sc_inner)
        self._fp.pack(pady=(0, 8))
        self._scan_lbl = tk.Label(sc_inner, text="READY",
                                  font=("Courier", 9, "bold"), bg=CARD2, fg=MUTED)
        self._scan_lbl.pack()
        self._scan_sub = tk.Label(sc_inner, text="Place finger when prompted",
                                  font=("Courier", 7), bg=CARD2, fg=MUTED, wraplength=200)
        self._scan_sub.pack(pady=(2, 0))

        # ── LIVE DASHBOARD ────────────────────────────
        tk.Label(parent, text="LIVE DASHBOARD",
                 font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 8))

        dash = tk.Frame(parent, bg=BG)
        dash.pack(fill=tk.X)

        # Row 1: Checked In | Checked Out
        row1 = tk.Frame(dash, bg=BG); row1.pack(fill=tk.X, pady=(0, 8))

        self._tile_checkedin  = self._make_dash_tile(row1, "CHECKED IN TODAY",  "0", ACCENT2, "#0d1f3f", side=tk.LEFT)
        self._tile_checkedout = self._make_dash_tile(row1, "CHECKED OUT",       "0", GREEN2,  "#0a3321", side=tk.LEFT)

        # Row 2: Early Checkout (full width highlight)
        row2 = tk.Frame(dash, bg=BG); row2.pack(fill=tk.X, pady=(0, 8))
        self._tile_early = self._make_dash_tile(row2, f"LEFT BEFORE {EARLY_CHECKOUT_H:02d}:00", "0",
                                                 CYAN2, CYAN_DIM, side=tk.LEFT, full=True)

        # Row 3: Late | Overtime
        row3 = tk.Frame(dash, bg=BG); row3.pack(fill=tk.X, pady=(0, 8))
        self._tile_late = self._make_dash_tile(row3, "LATE ARRIVALS", "0", ORANGE2, "#3d1f00", side=tk.LEFT)
        self._tile_ot   = self._make_dash_tile(row3, "OVERTIME",      "0", PURPLE,  "#1e0a40", side=tk.LEFT)

        # Donut ring showing completion rate
        dr_frame = tk.Frame(parent, bg=CARD2,
                            highlightbackground=BORDER, highlightthickness=1)
        dr_frame.pack(fill=tk.X, pady=(0, 10))
        dr_inner = tk.Frame(dr_frame, bg=CARD2, pady=10, padx=16); dr_inner.pack(fill=tk.X)
        tk.Label(dr_inner, text="COMPLETION RATE",
                 font=("Courier", 7, "bold"), bg=CARD2, fg=MUTED).pack(anchor="w", pady=(0,6))
        dr_row = tk.Frame(dr_inner, bg=CARD2); dr_row.pack(fill=tk.X)
        self._donut = DonutRing(dr_row)
        self._donut.pack(side=tk.LEFT, padx=(0, 14))
        dr_legend = tk.Frame(dr_row, bg=CARD2); dr_legend.pack(side=tk.LEFT, fill=tk.Y)
        self._legend_lbl = tk.Label(dr_legend, text="0 of 0 workers\nhave checked out",
                                     font=("Courier", 8), bg=CARD2, fg=TEXT2,
                                     justify=tk.LEFT)
        self._legend_lbl.pack(anchor="w")
        self._early_lbl = tk.Label(dr_legend, text="",
                                    font=("Courier", 8), bg=CARD2, fg=CYAN2,
                                    justify=tk.LEFT)
        self._early_lbl.pack(anchor="w", pady=(6, 0))

        # ── Recent events ─────────────────────────────
        tk.Label(parent, text="RECENT EVENTS",
                 font=("Courier", 8, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(8, 6))
        ev_fr = tk.Frame(parent, bg=CARD,
                         highlightbackground=BORDER, highlightthickness=1)
        ev_fr.pack(fill=tk.BOTH, expand=True)
        self._event_box = tk.Text(ev_fr, font=("Courier", 8), bg=CARD, fg=TEXT2,
                                   relief=tk.FLAT, padx=10, pady=8,
                                   state=tk.DISABLED, cursor="arrow", height=7)
        self._event_box.pack(fill=tk.BOTH, expand=True)
        for tag, col in [("in", GREEN2), ("out", ACCENT2), ("warn", ORANGE2),
                          ("ts", MUTED), ("early", CYAN2)]:
            self._event_box.tag_config(tag, foreground=col)

    def _make_dash_tile(self, parent, label, value, fg, bg2,
                        side=tk.LEFT, full=False):
        """Create a KPI tile and return the value Label for later update."""
        tile = tk.Frame(parent, bg=CARD2, padx=14, pady=10,
                        highlightbackground=bg2, highlightthickness=1)
        if full:
            tile.pack(side=side, fill=tk.X, expand=True)
        else:
            tile.pack(side=side, fill=tk.X, expand=True, padx=(0, 6) if side==tk.LEFT else 0)
        val_lbl = tk.Label(tile, text=value,
                           font=("Courier", 26, "bold"), bg=CARD2, fg=fg)
        val_lbl.pack()
        tk.Label(tile, text=label, font=("Courier", 6, "bold"),
                 bg=CARD2, fg=TEXT2).pack()
        return val_lbl

    # ── FOOTER ──────────────────────────────────────────
    def _build_footer(self):
        _make_sep(self.root, BORDER2)
        foot = tk.Frame(self.root, bg=CARD, padx=28, pady=7)
        foot.pack(fill=tk.X, side=tk.BOTTOM)
        self._foot_lbl = tk.Label(foot, text="", font=("Courier", 8), bg=CARD, fg=MUTED)
        self._foot_lbl.pack(side=tk.LEFT)
        tk.Label(foot, text=(f"Shift {SHIFT_START_H:02d}:{SHIFT_START_M:02d} – "
                              f"{(SHIFT_START_H+SHIFT_HOURS)%24:02d}:{SHIFT_START_M:02d} "
                              f"· {SHIFT_HOURS}h standard · {GRACE_MINUTES}min grace · "
                              f"Early out < {EARLY_CHECKOUT_H:02d}:00"),
                 font=("Courier", 8), bg=CARD, fg=MUTED).pack(side=tk.RIGHT)

    # ── FLASH OVERLAY ───────────────────────────────────
    def _build_flash(self):
        self.flash = tk.Frame(self.root, bg=ACCENT)
        self.fi = tk.Label(self.flash, font=("Courier", 60, "bold"), bg=ACCENT, fg=WHITE)
        self.fi.place(relx=0.5, rely=0.28, anchor="center")
        self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
                           bg=ACCENT, fg=WHITE, wraplength=740)
        self.fm.place(relx=0.5, rely=0.45, anchor="center")
        self.fs = tk.Label(self.flash, font=("Courier", 12),
                           bg=ACCENT, fg="#c7d9ff", wraplength=740)
        self.fs.place(relx=0.5, rely=0.56, anchor="center")
        self.fx = tk.Label(self.flash, font=("Courier", 11, "bold"),
                           bg=ACCENT, fg=GOLD2, wraplength=740)
        self.fx.place(relx=0.5, rely=0.65, anchor="center")

    # ── CLOCK ───────────────────────────────────────────
    def _tick_clock(self):
        n = datetime.now()
        self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
        self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ── LIVE STATS ──────────────────────────────────────
    def _tick_stats(self):
        lock  = load_lock()
        cin   = lock.get("checked_in",  {})
        cout  = lock.get("checked_out", {})
        total = len(cin) + len(cout)

        # All who checked in today (in + out)
        total_in  = total
        total_out = len(cout)
        early     = count_early_checkouts(lock)
        late      = sum(1 for v in {**cin, **cout}.values()
                        if isinstance(v, dict) and v.get("is_late"))
        ot        = sum(1 for v in cout.values()
                        if isinstance(v, dict) and v.get("overtime_hours", 0) > 0)

        # Update tiles
        self._tile_checkedin.config(text=str(total_in))
        self._tile_checkedout.config(text=str(total_out))
        self._tile_early.config(text=str(early))
        self._tile_late.config(text=str(late))
        self._tile_ot.config(text=str(ot))

        # Donut
        fraction = (total_out / total_in) if total_in > 0 else 0
        donut_color = GREEN2 if fraction >= 0.8 else ORANGE2 if fraction >= 0.4 else ACCENT2
        self._donut.set_value(fraction, donut_color)
        self._legend_lbl.config(
            text=f"{total_out} of {total_in} workers\nhave checked out")
        if early > 0:
            self._early_lbl.config(
                text=f"⚡ {early} left before {EARLY_CHECKOUT_H:02d}:00")
        else:
            self._early_lbl.config(text="")

        self._foot_lbl.config(
            text=(f"Checked In: {total_in}  "
                  f"Out: {total_out}  "
                  f"On-site: {len(cin)}  "
                  f"Early: {early}  "
                  f"Late: {late}  "
                  f"OT: {ot}"))

        self.root.after(6000, self._tick_stats)

    # ── ADMIN ───────────────────────────────────────────
    def _open_admin(self): AdminPanel(self.root)

    # ── EXPORT ──────────────────────────────────────────
    def _quick_export(self):
        fname = export_daily_summary()
        if fname:
            self.log(f"Exported → {os.path.abspath(fname)}", "ok")
            self._add_event("Export", fname, "ts")
        else:
            self.log("Nothing to export — no records today.", "warn")

    # ── LOGGING ─────────────────────────────────────────
    def log(self, msg, tag="info"):
        def _do():
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] ", "ts")
            self.log_box.insert(tk.END, f"{msg}\n", tag)
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    def _add_event(self, action, name, tag="ts"):
        def _do():
            self._event_box.config(state=tk.NORMAL)
            ts = datetime.now().strftime("%H:%M")
            self._event_box.insert("1.0", f"{ts} {action:<10} {name}\n", tag)
            self._event_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    # ── FLASH ───────────────────────────────────────────
    def _show_flash(self, icon, headline, sub, extra, color):
        self.flash.config(bg=color)
        for w, v in [(self.fi, icon), (self.fm, headline),
                     (self.fs, sub), (self.fx, extra)]:
            w.config(text=v, bg=color)
        self.flash.place(x=0, y=0, relwidth=1, relheight=1)
        self.flash.lift()
        self.root.after(2400, self.flash.place_forget)

    # ── SCANNER UI ──────────────────────────────────────
    def _scan_start(self):
        self._fp.start()
        self._scan_lbl.config(text="SCANNING…", fg=ORANGE2)
        self._scan_sub.config(text="Place your finger on the reader now")

    def _scan_ok(self):
        self._fp.stop_ok()
        self._scan_lbl.config(text="CAPTURED ✔", fg=GREEN2)
        self._scan_sub.config(text="Processing…")

    def _scan_err(self, msg="FAILED"):
        self._fp.stop_err(msg)
        self._scan_lbl.config(text=msg, fg=RED2)
        self._scan_sub.config(text="Please try again")

    def _scan_reset(self):
        self._fp.reset()
        self._scan_lbl.config(text="READY", fg=MUTED)
        self._scan_sub.config(text="Place finger when prompted")

    # ── STATUS & BUTTONS ────────────────────────────────
    def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
        def _do():
            self.sf.config(bg=bg, highlightbackground=border)
            for w in self.sf.winfo_children():
                for iw in ([w] + list(w.winfo_children())):
                    try: iw.config(bg=bg)
                    except Exception: pass
            self.sl.config(text=text, fg=fg, bg=bg)
            self._status_led.config(bg=bg)
            self._status_led.set_color(fg)
            self._led.set_color(fg)
        self.root.after(0, _do)

    def _set_buttons(self, in_s, out_s):
        def _do():
            self.btn_in.config(
                state=in_s,
                bg=GREEN if in_s == tk.NORMAL else GREEN_DIM,
                fg=BG    if in_s == tk.NORMAL else MUTED)
            self.btn_out.config(
                state=out_s,
                bg=RED   if out_s == tk.NORMAL else RED_DIM,
                fg=WHITE if out_s == tk.NORMAL else MUTED)
        self.root.after(0, _do)

    def _set_avatar(self, name=None, color=BORDER):
        initials = _initials(name) if name else ""
        self._avatar_cv.itemconfig(self._avatar_circle, fill=color)
        self._avatar_cv.itemconfig(self._avatar_text, text=initials,
                                   fill=WHITE if name else MUTED)

    def _apply_status(self, status, name=None):
        if status == "done":
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status("Attendance complete — see you tomorrow", RED, RED_DIM, RED)
            self._set_avatar(name, RED_DIM)
        elif status == "checked_in":
            self._set_buttons(tk.DISABLED, tk.NORMAL)
            self._set_status("Already checked IN — proceed to Check-Out", ORANGE, ORANGE_DIM, ORANGE)
            self._set_avatar(name, ORANGE_DIM)
        elif status == "none":
            self._set_buttons(tk.NORMAL, tk.DISABLED)
            self._set_status("Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
            self._set_avatar(name, GREEN_DIM)
        else:
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
            self._set_avatar(None, BORDER)

    # ── ID VALIDATION ───────────────────────────────────
    def _on_key(self, _=None):
        if self._debounce_job:
            self.root.after_cancel(self._debounce_job)
        uid = self.user_entry.get().strip()
        if not uid:
            self._soft_reset(); return
        self._apply_status(get_worker_status(uid))
        self._debounce_job = self.root.after(
            650, lambda: threading.Thread(
                target=self._validate, args=(uid,), daemon=True).start())

    def _validate(self, uid):
        if self.user_entry.get().strip() != uid or self._busy: return
        worker = self._worker_cache.get(uid) or find_worker(uid)
        if worker: self._worker_cache[uid] = worker
        if self.user_entry.get().strip() != uid: return
        def _upd():
            if not worker:
                self.name_lbl.config(text="Unknown ID", fg=RED2)
                self.hint_lbl.config(text=f"ID '{uid}' not found — contact admin", fg=RED)
                self._set_buttons(tk.DISABLED, tk.DISABLED)
                self._set_status(f"Worker ID {uid} does not exist", RED, RED_DIM, RED)
                self._set_avatar(None, RED_DIM)
            else:
                name   = worker.get("Full_Name", "N/A")
                status = get_worker_status(uid)
                self.name_lbl.config(text=name, fg=WHITE)
                hints = {
                    "checked_in": ("Checked in today — use Check-Out", ORANGE),
                    "done":        ("Attendance complete for today",    RED),
                    "none":        ("Not yet checked in today",          TEXT2),
                }
                htxt, hcol = hints.get(status, ("", TEXT2))
                self.hint_lbl.config(text=htxt, fg=hcol)
                self._apply_status(status, name)
        self.root.after(0, _upd)

    def _on_enter(self, _=None):
        uid = self.user_entry.get().strip()
        if not uid or self._busy: return
        s = get_worker_status(uid)
        if s == "none":       self._trigger("checkin")
        elif s == "checked_in": self._trigger("checkout")

    # ── TRIGGER ─────────────────────────────────────────
    def _trigger(self, action):
        if self._busy: return
        uid = self.user_entry.get().strip()
        if not uid: return
        self._busy = True
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        verb = "CHECK IN" if action == "checkin" else "CHECK OUT"
        self._set_status(f"Scanning fingerprint for {verb}…", ORANGE, ORANGE_DIM, ORANGE)
        self.root.after(0, self._scan_start)
        threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

    # ── MAIN WORKER THREAD ──────────────────────────────
    def _process(self, uid, action):
        is_open = False
        success = False
        msg     = ""
        full_name = uid
        try:
            self.log(f"{'─'*18} {action.upper()} · ID {uid} {'─'*18}", "div")
            if zk.GetDeviceCount() == 0:
                self.log("Scanner not connected", "err")
                self.root.after(0, lambda: self._scan_err("NO DEVICE"))
                self.root.after(0, lambda: self._show_flash(
                    "⚠", "Scanner Not Connected",
                    "Connect the fingerprint device and try again.", "", "#6d28d9"))
                return
            zk.OpenDevice(0); is_open = True
            self.log("Waiting for fingerprint…", "info")
            capture = None
            for _ in range(150):
                capture = zk.AcquireFingerprint()
                if capture: break
                time.sleep(0.2)
            if not capture:
                self.log("Scan timed out", "err")
                self.root.after(0, lambda: self._scan_err("TIMEOUT"))
                self.root.after(0, lambda: self._show_flash(
                    "⏱", "Scan Timeout", "No fingerprint detected.", "", "#92400e"))
                return
            self.root.after(0, self._scan_ok)
            self.log("Fingerprint captured ✔", "ok")
            worker = self._worker_cache.get(uid) or find_worker(uid)
            if worker: self._worker_cache[uid] = worker
            if not worker:
                self.log(f"ID {uid} not found in Zoho", "err")
                self.root.after(0, lambda: self._scan_err("NOT FOUND"))
                self.root.after(0, lambda: self._show_flash(
                    "✗", "Worker Not Found", f"ID {uid} does not exist.", "", RED_DIM))
                return
            full_name = worker.get("Full_Name", uid)
            self.log(f"Identity: {full_name}", "ok")
            status = get_worker_status(uid)
            if status == "done":
                self.log("Attendance already complete today", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "🔒", "Already Complete", full_name, "Done for today.", "#1e0a40"))
                self.root.after(2600, lambda: self._apply_status("done", full_name))
                return
            if status == "checked_in" and action == "checkin":
                self.log("Already checked IN", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "↩", "Already Checked In", full_name, "Use Check-Out instead.", "#3d1f00"))
                self.root.after(2600, lambda: self._apply_status("checked_in", full_name))
                return
            if status == "none" and action == "checkout":
                self.log("Not checked IN yet", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "⚠", "Not Checked In", full_name, "Check IN first.", "#1e0a40"))
                self.root.after(2600, lambda: self._apply_status("none", full_name))
                return
            self.log(f"Posting {action.upper()} to Zoho…", "info")
            pa  = worker.get("Projects_Assigned")
            pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID
            success, msg = log_attendance(worker["ID"], uid, pid, full_name, action, self.log)
            tag = "ok" if success else "err"
            for line in msg.splitlines():
                if line.strip():
                    ltag = tag
                    if "late" in line.lower():     ltag = "late"
                    if "overtime" in line.lower(): ltag = "ot"
                    if "early" in line.lower():    ltag = "early"
                    self.log(line.strip(), ltag)
            if success:
                verb      = "Checked IN" if action == "checkin" else "Checked OUT"
                sub       = datetime.now().strftime("Time: %H:%M:%S · %A, %d %B %Y")
                extra     = ""
                flash_col = "#1d4ed8"
                if action == "checkin" and is_late(datetime.now()):
                    extra     = f"⚠ Late arrival — {late_by_str(datetime.now())}"
                    flash_col = "#92400e"
                if action == "checkout":
                    lock2 = load_lock()
                    co    = lock2.get("checked_out", {}).get(str(uid), {})
                    ot    = co.get("overtime_hours", 0) if isinstance(co, dict) else 0
                    now_  = datetime.now()
                    early_limit = now_.replace(hour=EARLY_CHECKOUT_H,
                                               minute=EARLY_CHECKOUT_M,
                                               second=0, microsecond=0)
                    if now_ < early_limit:
                        extra     = f"⚡ Early checkout — before {EARLY_CHECKOUT_H:02d}:00"
                        flash_col = CYAN_DIM
                    elif ot > 0:
                        extra = f"⏱ Overtime: {int(ot)}h {int((ot%1)*60)}m"
                ev_tag = "in" if action == "checkin" else "out"
                self._add_event(verb, full_name, ev_tag)
                self._tick_stats()
                _v, _s, _e, _fc = verb, sub, extra, flash_col
                self.root.after(0, lambda: self._show_flash(
                    "✔", f"{_v} — {full_name}", _s, _e, _fc))
            else:
                _m = msg.splitlines()[0][:80]
                self.root.after(0, lambda: self._scan_err("ERROR"))
                self.root.after(0, lambda: self._show_flash(
                    "✗", "Action Failed", _m, "", RED_DIM))
        except Exception as exc:
            self.log(f"Unexpected error: {exc}", "err")
        finally:
            if is_open:
                try: zk.CloseDevice()
                except: pass
            self._busy = False
            self.root.after(2600, self._scan_reset)
            self.root.after(2600, lambda: self._reset_ui(clear_log=success))

    # ── RESET ───────────────────────────────────────────
    def _reset_ui(self, clear_log=False):
        self.user_entry.delete(0, tk.END)
        self.name_lbl.config(text="—", fg=MUTED)
        self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
        self._set_avatar(None, BORDER)
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)
        if clear_log:
            self.log_box.config(state=tk.NORMAL)
            self.log_box.delete("1.0", tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.log("Ready for next worker.", "div")
        self.user_entry.focus_set()

    def _soft_reset(self):
        self.name_lbl.config(text="—", fg=MUTED)
        self.hint_lbl.config(text="Enter a Worker ID above", fg=MUTED)
        self._set_avatar(None, BORDER)
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        self._set_status("Awaiting Worker ID", ACCENT, ACCENT_DIM, ACCENT)

    # ── CLOSE ───────────────────────────────────────────
    def _on_close(self):
        try: zk.Terminate()
        except: pass
        self.root.destroy()

# ===========================================================
if __name__ == "__main__":
    root = tk.Tk()
    FingerprintGUI(root)
    root.mainloop()