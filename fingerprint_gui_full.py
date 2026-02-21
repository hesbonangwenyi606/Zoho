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



import os, time, json, requests, threading
from datetime import datetime
from dotenv import load_dotenv
from pyzkfp import ZKFP2
import tkinter as tk

# ===========================================================
# CONFIGURATION
# ===========================================================
load_dotenv()
ZOHO_DOMAIN        = os.getenv("ZOHO_DOMAIN", "zoho.com")
APP_OWNER          = "wavemarkpropertieslimited"
APP_NAME           = "real-estate-wages-system"
CLIENT_ID          = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET      = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN      = os.getenv("ZOHO_REFRESH_TOKEN")
WORKERS_REPORT     = "All_Workers"
ATTENDANCE_FORM    = "Daily_Attendance"
ATTENDANCE_REPORT  = "Daily_Attendance_Report"
DEFAULT_PROJECT_ID = "4838902000000391493"
TOKEN_CACHE        = {"token": None, "expires_at": 0}
API_DOMAIN         = f"https://creator.zoho.{ZOHO_DOMAIN.split('.')[-1]}/api/v2"
CHECKIN_LOCK_FILE  = "checkin_today.json"

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
    """Retry wrapper — keeps trying on network errors all day long."""
    kwargs.setdefault("timeout", 45)
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.request(method, url, **kwargs)
            return r
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError, OSError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(2 * attempt)
    return None

def get_access_token():
    """Always return a valid token — refreshes automatically throughout the day."""
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 120:
        return TOKEN_CACHE["token"]
    # Token expired or about to — refresh it
    TOKEN_CACHE["token"] = None   # clear so we never use a stale token
    url  = f"https://accounts.{ZOHO_DOMAIN}/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
    }
    # Try up to 3 times in case of transient network error
    for _ in range(3):
        r = zoho_request("POST", url, data=data, retries=1)
        if r and r.status_code == 200:
            result = r.json()
            TOKEN_CACHE["token"]      = result.get("access_token")
            TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
            return TOKEN_CACHE["token"]
        time.sleep(3)
    return None

def auth_headers():
    token = get_access_token()
    return {"Authorization": f"Zoho-oauthtoken {token}"} if token else {}

# ===========================================================
# LOCAL STATE — persists across the ENTIRE day
# ===========================================================
def load_lock():
    """
    Load today's attendance state from disk.
    File is keyed by date so it naturally resets at midnight —
    workers who check in at 7 AM can still check out at 6 PM.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(CHECKIN_LOCK_FILE):
        try:
            with open(CHECKIN_LOCK_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") == today:
                return data   # same day — return as-is (survives app restarts)
        except Exception:
            pass
    # New day or corrupt file — start fresh
    fresh = {"date": today, "checked_in": {}, "checked_out": {}}
    save_lock(fresh)
    return fresh

def save_lock(data):
    """Write state atomically so a crash never corrupts the file."""
    tmp = CHECKIN_LOCK_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CHECKIN_LOCK_FILE)   # atomic on all major OS

def get_worker_status(zk_id):
    lock = load_lock()
    key  = str(zk_id)
    if key in lock["checked_out"]:  return "done"
    if key in lock["checked_in"]:   return "checked_in"
    return "none"

def get_checkin_info(zk_id):
    """Return the stored {time, zoho_id} dict for this worker, or None."""
    return load_lock()["checked_in"].get(str(zk_id))

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

def _find_record_in_zoho(worker_id, today_display, today_iso, hdrs):
    """
    Fallback: search Zoho for today's attendance record when the
    local zoho_id is missing (e.g. after an app restart mid-day).
    Tries multiple criteria so it always finds the right record.
    """
    report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
    for crit in [
        f'(Worker_Name == {worker_id} && Date == "{today_display}")',
        f'(Worker_Name == {worker_id} && Date == "{today_iso}")',
        f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_display}")',
        f'(Worker_ID_Lookup == "{worker_id}" && Date == "{today_iso}")',
        f'(Worker_Name == {worker_id})',
    ]:
        r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
        if r and r.status_code == 200:
            recs = r.json().get("data", [])
            if recs:
                # If multiple, pick the one matching today
                for rec in recs:
                    d = str(rec.get("Date", rec.get("Date_field", ""))).strip()
                    if d in (today_display, today_iso):
                        return rec["ID"]
                # Fall back to the first record if date-match failed
                return recs[0]["ID"]
    return None

def log_attendance(worker_id, zk_id, project_id, full_name, action):
    now           = datetime.now()
    zk_key        = str(zk_id)
    today_display = now.strftime("%d-%b-%Y")
    today_iso     = now.strftime("%Y-%m-%d")

    # ── CHECK-IN ──────────────────────────────────────────
    if action == "checkin":
        form_url     = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
        checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
        hdrs = auth_headers()

        payload = {"data": {
            "Worker_Name":      worker_id,
            "Projects":         project_id,
            "Date":             today_display,
            "First_In":         checkin_time,
            "Worker_Full_Name": full_name,
        }}

        r = zoho_request("POST", form_url, headers=hdrs, json=payload)
        if r and r.status_code in (200, 201):
            res  = r.json()
            # Extract Zoho record ID from every known response structure
            zoho_rec_id = (
                res.get("data", {}).get("ID")
                or res.get("ID")
                or (res.get("data", [{}])[0].get("ID")
                    if isinstance(res.get("data"), list) else None)
            )
            lock = load_lock()
            lock["checked_in"][zk_key] = {
                "time":    checkin_time,
                "zoho_id": zoho_rec_id,
            }
            save_lock(lock)
            return True, f"✅  {full_name} checked IN at {now.strftime('%H:%M')}"
        err = r.text[:200] if r else "Timeout"
        return False, f"Check-in failed: {err}"

    # ── CHECK-OUT ─────────────────────────────────────────
    elif action == "checkout":
        lock = load_lock()
        info = lock["checked_in"].get(zk_key)
        if not info:
            return False, "No check-in record found for today."

        hdrs = auth_headers()
        if not hdrs:
            return False, "Could not refresh Zoho token — check internet connection."

        att_record_id = info.get("zoho_id")

        # ── If zoho_id missing (app restarted), search Zoho ───────────
        if not att_record_id:
            att_record_id = _find_record_in_zoho(
                worker_id, today_display, today_iso, hdrs)

        if not att_record_id:
            return False, (
                f"Could not locate today's attendance record in Zoho.\n"
                f"Worker: {full_name}  Date: {today_display}\n"
                "Please check Daily_Attendance_Report manually."
            )

        # ── Calculate hours ────────────────────────────────────────────
        checkin_time_str = info.get("time", "")
        try:
            dt_in = datetime.strptime(checkin_time_str, "%d-%b-%Y %H:%M:%S")
        except Exception:
            dt_in = now
        total_hours = max((now - dt_in).total_seconds() / 3600, 0.01)
        total_str   = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

        # ── PATCH the record ───────────────────────────────────────────
        update_url = (
            f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}"
            f"/report/{ATTENDANCE_REPORT}/{att_record_id}"
        )
        r_u = zoho_request(
            "PATCH", update_url,
            headers=hdrs,
            json={"data": {
                "Last_Out":    now.strftime("%d-%b-%Y %H:%M:%S"),
                "Total_Hours": round(total_hours, 4),
            }},
        )

        if r_u and r_u.status_code == 200:
            body = r_u.json()
            code = body.get("code")
            if code == 3000:
                lock["checked_in"].pop(zk_key, None)
                lock["checked_out"][zk_key] = now.strftime("%H:%M:%S")
                save_lock(lock)
                return True, (
                    f"🚪  {full_name} checked OUT at {now.strftime('%H:%M')}\n"
                    f"    Total time worked: {total_str}"
                )
            # Zoho returned 200 but with a non-success code
            return False, f"Zoho error (code {code}): {body.get('message', '')}"

        http = r_u.status_code if r_u else "timeout"
        body = r_u.text[:200] if r_u else "No response"
        return False, f"Check-out failed (HTTP {http}): {body}"

    return False, "Unknown action."


# ===========================================================
# COLOUR PALETTE
# ===========================================================
BG         = "#060810"
CARD       = "#0d1117"
CARD2      = "#111827"
BORDER     = "#1e2433"
ACCENT     = "#3b82f6"
ACCENT_DIM = "#1d3a6e"
GREEN      = "#10b981"
GREEN_DIM  = "#064e35"
RED        = "#ef4444"
RED_DIM    = "#450a0a"
ORANGE     = "#f59e0b"
ORANGE_DIM = "#451a03"
TEXT       = "#f1f5f9"
MUTED      = "#475569"
WHITE      = "#ffffff"
GOLD       = "#fbbf24"


# ===========================================================
# GUI
# ===========================================================
class FingerprintGUI:
    def __init__(self, root):
        self.root         = root
        self.root.title("Real Estate Wages System")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._busy         = False
        self._debounce_job = None
        self._worker_cache = {}   # uid → worker dict (lives for the session)

        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        W, H   = min(sw, 860), min(sh, 720)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        self._build_ui()
        self._tick_clock()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── BUILD ─────────────────────────────────────────────
    def _build_ui(self):
        # HEADER
        hdr = tk.Frame(self.root, bg=CARD)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg=GOLD, height=3).pack(fill=tk.X)

        hi = tk.Frame(hdr, bg=CARD, padx=28, pady=16)
        hi.pack(fill=tk.X)

        lf = tk.Frame(hi, bg=CARD)
        lf.pack(side=tk.LEFT)
        tk.Label(lf, text="REAL ESTATE WAGES SYSTEM",
                 font=("Courier", 14, "bold"), bg=CARD, fg=GOLD).pack(anchor="w")
        tk.Label(lf, text="Wavemark Properties Limited  ·  Attendance Terminal",
                 font=("Courier", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2,0))

        rf = tk.Frame(hi, bg=CARD)
        rf.pack(side=tk.RIGHT)
        self.date_lbl  = tk.Label(rf, text="", font=("Courier", 9),
                                   bg=CARD, fg=MUTED)
        self.date_lbl.pack(anchor="e")
        self.clock_lbl = tk.Label(rf, text="", font=("Courier", 22, "bold"),
                                   bg=CARD, fg=WHITE)
        self.clock_lbl.pack(anchor="e")

        # BODY
        body = tk.Frame(self.root, bg=BG, padx=32, pady=20)
        body.pack(fill=tk.BOTH, expand=True)

        # ID CARD
        id_card = tk.Frame(body, bg=CARD2,
                           highlightbackground=BORDER, highlightthickness=1)
        id_card.pack(fill=tk.X, pady=(0, 16))
        id_i = tk.Frame(id_card, bg=CARD2, padx=20, pady=16)
        id_i.pack(fill=tk.X)

        tk.Label(id_i, text="WORKER ID", font=("Courier", 8, "bold"),
                 bg=CARD2, fg=MUTED).pack(anchor="w")

        er = tk.Frame(id_i, bg=CARD2)
        er.pack(fill=tk.X, pady=(6, 0))

        eb = tk.Frame(er, bg=GOLD, padx=2, pady=2)
        eb.pack(side=tk.LEFT)
        ei = tk.Frame(eb, bg="#0a0e1a")
        ei.pack()
        self.user_entry = tk.Entry(ei, font=("Courier", 26, "bold"),
                                   width=10, bd=0, bg="#0a0e1a", fg=WHITE,
                                   insertbackground=GOLD, selectbackground=GOLD)
        self.user_entry.pack(padx=12, pady=8)
        self.user_entry.bind("<KeyRelease>", self._on_key)
        self.user_entry.bind("<Return>",     self._on_enter)
        self.user_entry.focus_set()

        nc = tk.Frame(id_i, bg=CARD2)
        nc.pack(fill=tk.X, pady=(10, 0))
        self.name_lbl = tk.Label(nc, text="", font=("Courier", 15, "bold"),
                                  bg=CARD2, fg=GREEN)
        self.name_lbl.pack(anchor="w")
        self.hint_lbl = tk.Label(nc, text="", font=("Courier", 9),
                                  bg=CARD2, fg=MUTED)
        self.hint_lbl.pack(anchor="w")

        # STATUS BANNER
        self.sf = tk.Frame(body, bg=ACCENT_DIM,
                           highlightbackground=ACCENT, highlightthickness=1)
        self.sf.pack(fill=tk.X, pady=(0, 16))
        self.sl = tk.Label(self.sf, text="◉   Enter Worker ID to begin",
                           font=("Courier", 10), bg=ACCENT_DIM, fg=ACCENT,
                           pady=11, padx=16, anchor="w")
        self.sl.pack(fill=tk.X)

        # BUTTONS
        br = tk.Frame(body, bg=BG)
        br.pack(fill=tk.X, pady=(0, 16))

        self.btn_in = tk.Button(br, text="▶   CHECK  IN",
                                font=("Courier", 12, "bold"), width=18,
                                relief=tk.FLAT, bg=GREEN_DIM, fg=MUTED,
                                activebackground=GREEN, activeforeground=BG,
                                cursor="hand2", state=tk.DISABLED,
                                command=lambda: self._trigger("checkin"))
        self.btn_in.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

        self.btn_out = tk.Button(br, text="◼   CHECK  OUT",
                                 font=("Courier", 12, "bold"), width=18,
                                 relief=tk.FLAT, bg=RED_DIM, fg=MUTED,
                                 activebackground=RED, activeforeground=WHITE,
                                 cursor="hand2", state=tk.DISABLED,
                                 command=lambda: self._trigger("checkout"))
        self.btn_out.pack(side=tk.LEFT, ipady=10, padx=(0, 12))

        tk.Button(br, text="✕ CLEAR", font=("Courier", 9, "bold"),
                  relief=tk.FLAT, bg=BORDER, fg=MUTED,
                  activebackground=MUTED, activeforeground=WHITE,
                  cursor="hand2", command=self._reset_ui
                  ).pack(side=tk.LEFT, ipady=10)

        # DIVIDER
        tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

        # LOG
        lh = tk.Frame(body, bg=BG)
        lh.pack(fill=tk.X, pady=(0, 6))
        tk.Label(lh, text="ACTIVITY LOG", font=("Courier", 8, "bold"),
                 bg=BG, fg=MUTED).pack(side=tk.LEFT)
        tk.Button(lh, text="CLEAR LOG", font=("Courier", 7, "bold"),
                  relief=tk.FLAT, bg=BORDER, fg=MUTED, padx=6, pady=2,
                  cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

        lw = tk.Frame(body, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
        lw.pack(fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lw, bg=BORDER, troughcolor=CARD2)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box = tk.Text(lw, font=("Courier", 10), bg=CARD2, fg=TEXT,
                               relief=tk.FLAT, padx=12, pady=10,
                               yscrollcommand=sb.set, state=tk.DISABLED)
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.log_box.yview)

        for tag, col in [("ok", GREEN), ("err", RED), ("warn", ORANGE),
                         ("info", ACCENT), ("ts", MUTED), ("div", BORDER)]:
            self.log_box.tag_config(tag, foreground=col)

        # FLASH OVERLAY
        self.flash = tk.Frame(self.root, bg=ACCENT)
        self.fi = tk.Label(self.flash, font=("Courier", 64, "bold"), bg=ACCENT, fg=WHITE)
        self.fi.place(relx=0.5, rely=0.35, anchor="center")
        self.fm = tk.Label(self.flash, font=("Courier", 22, "bold"),
                           bg=ACCENT, fg=WHITE, wraplength=700)
        self.fm.place(relx=0.5, rely=0.52, anchor="center")
        self.fs = tk.Label(self.flash, font=("Courier", 13),
                           bg=ACCENT, fg="#c7d9ff", wraplength=700)
        self.fs.place(relx=0.5, rely=0.63, anchor="center")

    # ── CLOCK ─────────────────────────────────────────────
    def _tick_clock(self):
        n = datetime.now()
        self.date_lbl.config(text=n.strftime("%A, %d %B %Y"))
        self.clock_lbl.config(text=n.strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ── LOGGING ───────────────────────────────────────────
    def log(self, msg, tag="info"):
        def _do():
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END,
                f"[{datetime.now().strftime('%H:%M:%S')}]  ", "ts")
            self.log_box.insert(tk.END, f"{msg}\n", tag)
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ── FLASH ─────────────────────────────────────────────
    def _show_flash(self, icon, headline, sub, color):
        self.flash.config(bg=color)
        for w, v in [(self.fi, icon), (self.fm, headline), (self.fs, sub)]:
            w.config(text=v, bg=color)
        self.flash.place(x=0, y=0, relwidth=1, relheight=1)
        self.flash.lift()
        self.root.after(2000, self.flash.place_forget)

    # ── STATUS & BUTTONS ──────────────────────────────────
    def _set_status(self, text, fg=ACCENT, bg=ACCENT_DIM, border=ACCENT):
        def _do():
            self.sf.config(bg=bg, highlightbackground=border)
            self.sl.config(text=text, fg=fg, bg=bg)
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

    def _apply_status(self, status):
        if status == "done":
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status("◉   Attendance complete — see you tomorrow!",
                             RED, RED_DIM, RED)
        elif status == "checked_in":
            self._set_buttons(tk.DISABLED, tk.NORMAL)
            self._set_status("◉   Already CHECKED IN — proceed to Check-Out",
                             ORANGE, ORANGE_DIM, ORANGE)
        elif status == "none":
            self._set_buttons(tk.NORMAL, tk.DISABLED)
            self._set_status("◉   Ready to CHECK IN", GREEN, GREEN_DIM, GREEN)
        else:
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status("◉   Enter Worker ID to begin",
                             ACCENT, ACCENT_DIM, ACCENT)

    # ── ID VALIDATION (debounced, no fingerprint needed) ──
    def _on_key(self, _=None):
        if self._debounce_job:
            self.root.after_cancel(self._debounce_job)
        uid = self.user_entry.get().strip()
        if not uid:
            self._soft_reset(); return
        # Instant local status (from file)
        self._apply_status(get_worker_status(uid))
        # Delayed Zoho lookup after 700ms of no typing
        self._debounce_job = self.root.after(
            700, lambda: threading.Thread(
                target=self._validate, args=(uid,), daemon=True).start())

    def _validate(self, uid):
        """Silently validate ID against Zoho; update UI when done."""
        if self.user_entry.get().strip() != uid or self._busy:
            return
        if uid in self._worker_cache:
            worker = self._worker_cache[uid]
        else:
            worker = find_worker(uid)
            if worker:
                self._worker_cache[uid] = worker

        if self.user_entry.get().strip() != uid:
            return

        def _upd():
            if not worker:
                self.name_lbl.config(text="", fg=RED)
                self.hint_lbl.config(
                    text=f"✗  ID '{uid}' not found — contact admin", fg=RED)
                self._set_buttons(tk.DISABLED, tk.DISABLED)
                self._set_status(f"◉   Worker ID {uid} does not exist",
                                 RED, RED_DIM, RED)
            else:
                name   = worker.get("Full_Name", "N/A")
                status = get_worker_status(uid)
                self.name_lbl.config(text=name, fg=GREEN)
                hints = {
                    "checked_in": ("Already checked IN — use Check-Out ↓", ORANGE),
                    "done":       ("Attendance complete for today", RED),
                    "none":       ("Ready to check in", MUTED),
                }
                htxt, hcol = hints.get(status, ("", MUTED))
                self.hint_lbl.config(text=htxt, fg=hcol)
                self._apply_status(status)
        self.root.after(0, _upd)

    def _on_enter(self, _=None):
        uid = self.user_entry.get().strip()
        if not uid or self._busy: return
        s = get_worker_status(uid)
        if s == "none":        self._trigger("checkin")
        elif s == "checked_in": self._trigger("checkout")

    # ── TRIGGER ───────────────────────────────────────────
    def _trigger(self, action):
        if self._busy: return
        uid = self.user_entry.get().strip()
        if not uid: return
        self._busy = True
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        self._set_status("◉   Scanning fingerprint...", ORANGE, ORANGE_DIM, ORANGE)
        threading.Thread(target=self._process, args=(uid, action), daemon=True).start()

    # ── MAIN WORKER THREAD ────────────────────────────────
    def _process(self, uid, action):
        is_open  = False
        success  = False
        msg      = ""
        full_name = uid

        try:
            self.log(f"{'─'*20} {action.upper()} · ID {uid} {'─'*20}", "div")

            # ── Fingerprint device ───────────────────────
            if zk.GetDeviceCount() == 0:
                self.log("Scanner not connected", "err")
                self.root.after(0, lambda: self._show_flash(
                    "⚠", "Scanner Not Connected",
                    "Connect the fingerprint device and try again.", "#7c3aed"))
                return

            zk.OpenDevice(0)
            is_open = True
            self.log("Place your finger on the scanner...", "info")

            capture = None
            for _ in range(150):  # up to 30 s
                capture = zk.AcquireFingerprint()
                if capture: break
                time.sleep(0.2)

            if not capture:
                self.log("Scan timed out — please try again", "err")
                self.root.after(0, lambda: self._show_flash(
                    "⏱", "Scan Timeout", "No fingerprint detected.", "#b45309"))
                return

            self.log("Fingerprint captured ✔", "ok")

            # ── Worker lookup ─────────────────────────────
            worker = self._worker_cache.get(uid) or find_worker(uid)
            if worker:
                self._worker_cache[uid] = worker
            if not worker:
                self.log(f"ID {uid} not found in Zoho", "err")
                self.root.after(0, lambda: self._show_flash(
                    "✗", "Worker Not Found",
                    f"ID {uid} does not exist in the system.", RED))
                return

            full_name = worker.get("Full_Name", uid)
            self.log(f"Worker: {full_name}", "ok")

            # ── Guard checks ──────────────────────────────
            status = get_worker_status(uid)
            if status == "done":
                self.log("Attendance already complete today", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "🔒", "Already Done", full_name, "#7c3aed"))
                self.root.after(2200, lambda: self._apply_status("done"))
                return
            if status == "checked_in" and action == "checkin":
                self.log("Already checked IN — redirecting to Check-Out", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "↩", "Already Checked In",
                    f"{full_name} — please use Check-Out", "#92400e"))
                self.root.after(2200, lambda: self._apply_status("checked_in"))
                return
            if status == "none" and action == "checkout":
                self.log("Not checked IN yet — check in first", "warn")
                self.root.after(0, lambda: self._show_flash(
                    "⚠", "Not Checked In",
                    f"{full_name} — check IN first", "#7c3aed"))
                self.root.after(2200, lambda: self._apply_status("none"))
                return

            # ── Post to Zoho ──────────────────────────────
            self.log(f"Posting {action.upper()} to Zoho...", "info")
            pa  = worker.get("Projects_Assigned")
            pid = pa.get("ID") if isinstance(pa, dict) else DEFAULT_PROJECT_ID

            success, msg = log_attendance(
                worker["ID"], uid, pid, full_name, action)

            tag = "ok" if success else "err"
            for line in msg.splitlines():
                if line.strip():
                    self.log(line.strip(), tag)

            if success:
                verb = "Checked IN" if action == "checkin" else "Checked OUT"
                sub  = datetime.now().strftime("Time: %H:%M:%S  ·  %A, %d %B %Y")
                self.root.after(0, lambda: self._show_flash(
                    "✔", f"{verb}  —  {full_name}", sub, "#1d4ed8"))
            else:
                self.root.after(0, lambda: self._show_flash(
                    "✗", "Action Failed", msg.splitlines()[0][:80], RED))

        except Exception as exc:
            self.log(f"Unexpected error: {exc}", "err")

        finally:
            if is_open:
                try: zk.CloseDevice()
                except: pass
            self._busy = False
            # 2.2 s — flash finishes, then wipe everything for next worker
            self.root.after(2200, lambda: self._reset_ui(clear_log=success))

    # ── RESET ─────────────────────────────────────────────
    def _reset_ui(self, clear_log=False):
        """Clear all fields and optionally wipe the log for the next worker."""
        self.user_entry.delete(0, tk.END)
        self.name_lbl.config(text="")
        self.hint_lbl.config(text="")
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        self._set_status("◉   Enter Worker ID to begin",
                         ACCENT, ACCENT_DIM, ACCENT)
        if clear_log:
            self.log_box.config(state=tk.NORMAL)
            self.log_box.delete("1.0", tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.log("Ready for next worker.", "div")
        self.user_entry.focus_set()

    def _soft_reset(self):
        self.name_lbl.config(text="")
        self.hint_lbl.config(text="")
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        self._set_status("◉   Enter Worker ID to begin",
                         ACCENT, ACCENT_DIM, ACCENT)

    # ── CLOSE ─────────────────────────────────────────────
    def _on_close(self):
        try: zk.Terminate()
        except: pass
        self.root.destroy()


# ===========================================================
if __name__ == "__main__":
    root = tk.Tk()
    FingerprintGUI(root)
    root.mainloop()