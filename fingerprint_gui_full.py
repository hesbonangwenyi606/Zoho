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
MAX_RETRIES        = 3          # reduced: PATCH is not safely idempotent
RETRY_DELAY        = 2
TIMEOUT            = 45         # increased from 20 → 45 seconds
PATCH_TIMEOUT      = 60         # extra-long timeout specifically for PATCH
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# ===========================================================
# NETWORK HELPER
# ===========================================================
def zoho_request(method, url, *, retries=MAX_RETRIES,
                 expected_statuses=(200, 201), timeout=None, **kwargs):
    kwargs.setdefault("timeout", timeout or TIMEOUT)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code in expected_statuses:
                return resp
            if resp.status_code in RETRYABLE_STATUSES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            return resp
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, OSError) as e:
            if attempt == retries:
                return None
            time.sleep(RETRY_DELAY * attempt)
    return None

# ===========================================================
# CHECKIN LOCK
# ===========================================================
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

def is_checked_in_today(zk_user_id):
    return load_checkin_lock()["checked_in"].get(str(zk_user_id))

def is_checked_out_today(zk_user_id):
    return str(zk_user_id) in load_checkin_lock().get("checked_out", {})

def mark_checked_in(zk_user_id, time_str):
    lock = load_checkin_lock()
    lock["checked_in"][str(zk_user_id)] = time_str
    with open(CHECKIN_LOCK_FILE, "w") as f:
        json.dump(lock, f)

def mark_checked_out(zk_user_id):
    lock = load_checkin_lock()
    lock["checked_in"].pop(str(zk_user_id), None)
    lock.setdefault("checked_out", {})[str(zk_user_id)] = \
        datetime.now().strftime("%H:%M:%S")
    with open(CHECKIN_LOCK_FILE, "w") as f:
        json.dump(lock, f)

def get_worker_status(zk_user_id):
    key = str(zk_user_id)
    if is_checked_out_today(key):
        return "done"
    if is_checked_in_today(key):
        return "checked_in"
    return "none"

# ===========================================================
# AUTHENTICATION
# ===========================================================
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
    r = zoho_request("POST", url, data=data, timeout=30)
    if r:
        result = r.json()
        TOKEN_CACHE["token"]      = result.get("access_token")
        TOKEN_CACHE["expires_at"] = now + int(result.get("expires_in", 3600))
        return TOKEN_CACHE["token"]
    return None

def auth_headers():
    token = get_access_token()
    if not token:
        raise RuntimeError("Could not obtain Zoho access token.")
    return {"Authorization": f"Zoho-oauthtoken {token}"}

# ===========================================================
# WORKER LOOKUP
# ===========================================================
def find_worker(zk_user_id):
    url      = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{WORKERS_REPORT}"
    criteria = f"(ZKTeco_User_ID2 == {int(zk_user_id)})"
    r = zoho_request("GET", url, headers=auth_headers(),
                     params={"criteria": criteria})
    if r and r.status_code == 200:
        data = r.json().get("data", [])
        if data:
            return data[0]
    return None

# ===========================================================
# ATTENDANCE
# ===========================================================
def log_attendance(worker_id, zk_user_id, project_id, full_name, action):
    now      = datetime.now()
    form_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/form/{ATTENDANCE_FORM}"
    zk_key   = str(zk_user_id)

    today_display = now.strftime("%d-%b-%Y")
    today_iso     = now.strftime("%Y-%m-%d")
    today_mmdd    = now.strftime("%m/%d/%Y")

    # ----------------------------------------------------------
    # CHECK-IN
    # ----------------------------------------------------------
    if action == "checkin":
        if is_checked_out_today(zk_key):
            return False, (
                f"{full_name} has already completed attendance for today. "
                "Only one check-in/out cycle is allowed per day."
            )
        if is_checked_in_today(zk_key):
            t = is_checked_in_today(zk_key)
            return False, (
                f"{full_name} already checked IN today at "
                f"{t.split(' ')[-1] if t else 'N/A'}. "
                "Please use Check-Out instead."
            )

        checkin_time = now.strftime("%d-%b-%Y %H:%M:%S")
        # Resolve token ONCE before the POST
        hdrs = auth_headers()
        r = zoho_request(
            "POST", form_url,
            headers=hdrs,
            json={"data": {
                "Worker_ID_Lookup":  worker_id,
                "Worker_Name":       worker_id,
                "Projects":          project_id,
                "Projects_Assigned": project_id,
                "Date":              today_display,
                "First_In":          checkin_time,
                "Worker_Full_Name":  full_name,
            }}
        )
        if r and r.status_code in (200, 201):
            mark_checked_in(zk_key, checkin_time)
            return True, f"[OK] {full_name} checked IN at {now.strftime('%H:%M')}"
        err = r.text if r else "No response"
        return False, (
            f"[ERROR] Check-in failed "
            f"(HTTP {r.status_code if r else '???'}): {err}"
        )

    # ----------------------------------------------------------
    # CHECK-OUT
    # ----------------------------------------------------------
    elif action == "checkout":
        if is_checked_out_today(zk_key):
            t = load_checkin_lock().get("checked_out", {}).get(zk_key, "N/A")
            return False, (
                f"{full_name} already checked OUT today at {t}. "
                "Only one check-in/out cycle is allowed per day."
            )

        checkin_time = is_checked_in_today(zk_key)
        if not checkin_time:
            return False, (
                f"{full_name} has not checked IN yet today. "
                "Please check IN first."
            )

        # Calculate hours worked
        try:
            first_dt = datetime.strptime(checkin_time, "%d-%b-%Y %H:%M:%S")
        except Exception:
            first_dt = now
        total_secs     = (now - first_dt).total_seconds()
        total_hours    = total_secs / 3600
        total_time_str = f"{int(total_hours)}h {int((total_hours % 1) * 60)}m"

        # ----------------------------------------------------------
        # FIX: Resolve auth token ONCE before all GET/PATCH calls.
        # Previously auth_headers() was called inside do_patch() which
        # triggered a fresh token request on every attempt, adding
        # latency and sometimes causing cascading timeouts.
        # ----------------------------------------------------------
        hdrs = auth_headers()

        report_url = f"{API_DOMAIN}/{APP_OWNER}/{APP_NAME}/report/{ATTENDANCE_REPORT}"
        records    = []

        # Strategy A: lookup ID + ISO date
        crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_iso}")'
        r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
        if r and r.status_code == 200:
            records = r.json().get("data", [])

        # Strategy B: lookup ID + display date
        if not records:
            crit = f'(Worker_Name.ID == "{worker_id}" && Date_field == "{today_display}")'
            r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
            if r and r.status_code == 200:
                records = r.json().get("data", [])

        # Strategy C: worker only, match date in Python
        if not records:
            crit = f'(Worker_Name.ID == "{worker_id}")'
            r = zoho_request("GET", report_url, headers=hdrs, params={"criteria": crit})
            if r and r.status_code == 200:
                raw      = r.json().get("data", [])
                possible = {today_display, today_iso, today_mmdd}
                records  = [
                    rec for rec in raw
                    if str(rec.get("Date_field", "")).strip() in possible
                ]

        # Strategy D: no filter, match worker ID + date in Python
        if not records:
            r = zoho_request("GET", report_url, headers=hdrs)
            if r and r.status_code == 200:
                raw      = r.json().get("data", [])
                possible = {today_display, today_iso, today_mmdd}
                records  = [
                    rec for rec in raw
                    if rec.get("Worker_Name", {}).get("ID") == worker_id
                    and str(rec.get("Date_field", "")).strip() in possible
                ]

        if not records:
            return False, (
                f"[ERROR] Check-out failed: attendance record not found.\n"
                f"   Worker Zoho ID : {worker_id}\n"
                f"   Dates tried    : {today_display} / {today_iso} / {today_mmdd}"
            )

        att_id = records[0]["ID"]

        # ----------------------------------------------------------
        # CHECKOUT STRATEGY: DELETE via report endpoint + re-POST
        # PATCH/PUT/DELETE on the form endpoint all timeout.
        # DELETE on the report endpoint works. POST on form works.
        # So: delete the incomplete record, repost it complete.
        # ----------------------------------------------------------
        last_out_val  = now.strftime("%d-%b-%Y %H:%M:%S")
        total_hrs_val = round(total_hours, 4)

        # Step 1: DELETE via report endpoint
        r_del = zoho_request(
            "DELETE", f"{report_url}/{att_id}",
            headers=hdrs,
            retries=2,
            timeout=PATCH_TIMEOUT,
        )
        del_ok = r_del and r_del.status_code in (200, 201, 204)
        del_status = r_del.status_code if r_del else "timeout"
        del_body   = r_del.text[:200] if r_del and r_del.text else ""

        # Step 2: POST complete record regardless of delete result
        r_post = zoho_request(
            "POST", form_url,
            headers=hdrs,
            json={"data": {
                "Worker_ID_Lookup":  worker_id,
                "Worker_Name":       worker_id,
                "Projects":          project_id,
                "Projects_Assigned": project_id,
                "Date":              today_display,
                "First_In":          checkin_time,
                "Last_Out":          last_out_val,
                "Total_Hours":       total_hrs_val,
                "Worker_Full_Name":  full_name,
                "Remarks": "" if del_ok else "DUPLICATE - delete original check-in record",
            }}
        )

        if r_post and r_post.status_code in (200, 201):
            mark_checked_out(zk_key)
            post_body = r_post.text[:300] if r_post.text else ""
            note = "" if del_ok else f"\n   WARNING: Original record (ID:{att_id}) may still exist. Remove manually."
            return True, (
                f"[OK] {full_name} checked OUT at {now.strftime('%H:%M')} "
                f"| Total: {total_time_str}{note}\n"
                f"   POST response: {post_body}"
            )

        err = r_post.text[:300] if r_post else "timeout"
        return False, (
            f"[ERROR] Check-out POST failed\n"
            f"   Delete status : {del_status} {del_body}\n"
            f"   POST status   : {r_post.status_code if r_post else 'timeout'}\n"
            f"   Response      : {err}"
        )

    return False, "[ERROR] Unknown action"


# ===========================================================
class FingerprintGUI:
    def __init__(self, root):
        self.root  = root
        self.root.title("Zoho Attendance Fingerprint System")
        self.root.geometry("640x560")
        self._busy = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg="#2c3e50", pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Zoho Attendance System",
                 font=("Arial", 15, "bold"),
                 bg="#2c3e50", fg="white").pack()

        inp = tk.Frame(self.root, pady=12)
        inp.pack()
        tk.Label(inp, text="User ID:", font=("Arial", 12)).pack(
            side=tk.LEFT, padx=6)
        self.user_entry = tk.Entry(inp, font=("Arial", 13), width=18)
        self.user_entry.pack(side=tk.LEFT, padx=6)
        self.user_entry.bind("<KeyRelease>", self._on_id_change)
        self.user_entry.focus_set()

        self.status_lbl = tk.Label(
            self.root, text="Enter a User ID to begin.",
            font=("Arial", 10, "italic"), fg="gray")
        self.status_lbl.pack(pady=4)

        btn_frame = tk.Frame(self.root, pady=6)
        btn_frame.pack()

        self.btn_in = tk.Button(
            btn_frame, text="Check-In", width=16,
            font=("Arial", 11, "bold"),
            bg="#28a745", fg="white",
            activebackground="#1e7e34",
            disabledforeground="#999999",
            state=tk.DISABLED,
            command=lambda: self._trigger("checkin")
        )
        self.btn_in.pack(side=tk.LEFT, padx=14, ipady=6)

        self.btn_out = tk.Button(
            btn_frame, text="Check-Out", width=16,
            font=("Arial", 11, "bold"),
            bg="#dc3545", fg="white",
            activebackground="#bd2130",
            disabledforeground="#999999",
            state=tk.DISABLED,
            command=lambda: self._trigger("checkout")
        )
        self.btn_out.pack(side=tk.LEFT, padx=14, ipady=6)

        tk.Frame(self.root, height=1, bg="#cccccc").pack(
            fill=tk.X, pady=6, padx=10)

        tk.Label(self.root, text="Activity Log:",
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=14)
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        sb = tk.Scrollbar(log_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box = tk.Text(
            log_frame, height=14, width=74,
            font=("Courier", 10),
            yscrollcommand=sb.set,
            state=tk.DISABLED
        )
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.log_box.yview)

    def log(self, msg):
        def _do():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END, f"[{ts}]  {msg}\n")
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _set_status(self, text, color="gray"):
        self.root.after(
            0, lambda: self.status_lbl.config(text=text, fg=color))

    def _set_buttons(self, in_state, out_state):
        def _do():
            self.btn_in.config(state=in_state)
            self.btn_out.config(state=out_state)
        self.root.after(0, _do)

    def _apply_status_ui(self, status):
        if status == "done":
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status(
                "Attendance complete for today - no further action allowed.",
                "red")
        elif status == "checked_in":
            self._set_buttons(tk.DISABLED, tk.NORMAL)
            self._set_status(
                "Already checked IN today - Check-Out is now available.",
                "darkorange")
        else:
            self._set_buttons(tk.NORMAL, tk.DISABLED)
            self._set_status(
                "Not yet checked in today - Check-In is available.",
                "darkgreen")

    def _on_id_change(self, _event=None):
        if self._busy:
            return
        uid = self.user_entry.get().strip()
        if not uid:
            self._set_buttons(tk.DISABLED, tk.DISABLED)
            self._set_status("Enter a User ID to begin.", "gray")
            return
        self._apply_status_ui(get_worker_status(uid))

    def _trigger(self, action):
        if self._busy:
            return
        uid = self.user_entry.get().strip()
        if not uid:
            return
        self._busy = True
        self._set_buttons(tk.DISABLED, tk.DISABLED)
        threading.Thread(
            target=self._process, args=(uid, action), daemon=True
        ).start()

    def _process(self, zk_user_id, action):
        zk          = None
        device_open = False
        try:
            zk = ZKFP2()
            zk.Init()
            if zk.GetDeviceCount() == 0:
                self.log("No fingerprint device found.")
                return
            zk.OpenDevice(0)
            device_open = True

            time.sleep(1)
            self.log("Place your finger on the scanner...")

            capture  = None
            max_wait = 30
            waited   = 0.0
            last_dot = 0

            while not capture:
                capture = zk.AcquireFingerprint()
                if not capture:
                    time.sleep(0.2)
                    waited += 0.2
                    if int(waited) > last_dot and int(waited) % 3 == 0:
                        self.log(f"  Waiting for finger... ({int(waited)}s)")
                        last_dot = int(waited)
                    if waited >= max_wait:
                        self.log("Fingerprint timeout - please try again.")
                        return

            tmp, img = capture
            self.log("Fingerprint captured successfully.")

            self.log("Looking up worker...")
            worker = find_worker(zk_user_id)
            if not worker:
                self.log("Worker not found in Zoho.")
                return

            full_name      = worker.get("Full_Name", "N/A")
            zoho_worker_id = worker["ID"]

            status = get_worker_status(zk_user_id)
            if status == "done":
                self.log(
                    f"{full_name} has already completed attendance today. "
                    "No further action until tomorrow.")
                self._apply_status_ui(status)
                return
            if status == "checked_in" and action == "checkin":
                t = is_checked_in_today(zk_user_id)
                self.log(
                    f"{full_name} already checked IN at "
                    f"{t.split(' ')[-1] if t else 'N/A'} today. "
                    "Use Check-Out instead.")
                self._apply_status_ui(status)
                return
            if status == "none" and action == "checkout":
                self.log(
                    f"{full_name} has not checked IN yet today. "
                    "Please check IN first.")
                self._apply_status_ui(status)
                return

            project_id = (
                worker.get("Projects_Assigned", {}).get("ID")
                or DEFAULT_PROJECT_ID
            )
            success, message = log_attendance(
                zoho_worker_id, zk_user_id, project_id, full_name, action
            )
            self.log(message)

            if success:
                self._apply_status_ui(get_worker_status(zk_user_id))

        except Exception as exc:
            self.log(f"ERROR: {exc}")

        finally:
            if zk and device_open:
                try:
                    zk.CloseDevice()
                    zk.Terminate()
                except Exception:
                    pass
            self._busy = False

            def _reset():
                self.user_entry.delete(0, tk.END)
                self._set_buttons(tk.DISABLED, tk.DISABLED)
                self._set_status("Enter a User ID to begin.", "gray")
                self.log("-" * 50 + "\nReady for next user.")
            self.root.after(0, _reset)


# ===========================================================
# MAIN
# ===========================================================
if __name__ == "__main__":
    root = tk.Tk()
    FingerprintGUI(root)
    root.mainloop()