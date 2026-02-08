import argparse
import base64
import json
import os
import sys
import time
from ctypes import *
from datetime import datetime

from dotenv import load_dotenv

from middleware_core import handle_punch, retry_pending

print("Script started...")

# ====================================
# LOAD ENVIRONMENT VARIABLES
# ====================================
load_dotenv()

DEVICE_ID = os.getenv("ZK_DEVICE_ID", "ZK9500_USB_FINGERPRINT")
FINGERPRINT_DB_FILE = os.getenv("FINGERPRINT_DB_FILE", "fingerprints.json")

DB_HANDLE = None
FID_TO_USER = {}
FP_IMG_BUF = None
FP_IMG_SIZE = 0
DEV_HANDLE = None

ERR_MAP = {
    0: "OK",
    -1: "INITLIB_FAIL",
    -2: "INIT_FAIL",
    -3: "NO_DEVICE",
    -4: "NOT_SUPPORTED",
    -5: "INVALID_PARAM",
    -6: "OPEN_FAIL",
    -7: "INVALID_HANDLE",
    -8: "CAPTURE_FAIL",
    -9: "EXTRACT_FAIL",
    -10: "ABORT",
    -11: "MEMORY_NOT_ENOUGH",
    -12: "BUSY",
    -13: "ADD_FINGER_FAIL",
    -14: "DEL_FINGER_FAIL",
    -17: "FAIL",
    -18: "CANCEL",
    -20: "VERIFY_FAIL",
    -22: "MERGE_FAIL",
    -23: "NOT_OPENED",
    -24: "NOT_INIT",
    -25: "ALREADY_OPENED",
    -26: "LOADIMAGE_FAIL",
    -27: "ANALYSE_IMG_FAIL",
    -28: "TIMEOUT",
}

# ====================================
# LOAD ZKTECO SDK DLL
# ====================================
def _resolve_dll_path():
    env_path = os.getenv("ZKFP_DLL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    for name in ("zkfp.dll", "libzkfp.dll"):
        candidate = os.path.join(os.getcwd(), name)
        if os.path.exists(candidate):
            return candidate
    return None


SDK_PATH = _resolve_dll_path()
if not SDK_PATH:
    print("ERROR: zkfp.dll/libzkfp.dll not found. Set ZKFP_DLL_PATH.")
    sys.exit(1)

try:
    zkfp = WinDLL(SDK_PATH)
    print(f"Loaded {os.path.basename(SDK_PATH)} successfully")
except Exception as e:
    print(f"Failed to load DLL: {e}")
    sys.exit(1)

def _set_api():
    zkfp.ZKFPM_Init.restype = c_int
    zkfp.ZKFPM_GetDeviceCount.restype = c_int
    zkfp.ZKFPM_OpenDevice.restype = c_void_p
    zkfp.ZKFPM_DBInit.restype = c_void_p
    zkfp.ZKFPM_CloseDevice.restype = c_int
    zkfp.ZKFPM_DBFree.restype = c_int
    zkfp.ZKFPM_Terminate.restype = c_int
    zkfp.ZKFPM_AcquireFingerprint.restype = c_int
    zkfp.ZKFPM_DBIdentify.restype = c_int
    zkfp.ZKFPM_DBAdd.restype = c_int
    zkfp.ZKFPM_DBMerge.restype = c_int
    zkfp.ZKFPM_DBMatch.restype = c_int

    zkfp.ZKFPM_OpenDevice.argtypes = [c_int]
    zkfp.ZKFPM_CloseDevice.argtypes = [c_void_p]
    zkfp.ZKFPM_DBInit.argtypes = []
    zkfp.ZKFPM_DBFree.argtypes = [c_void_p]
    zkfp.ZKFPM_Terminate.argtypes = []
    zkfp.ZKFPM_AcquireFingerprint.argtypes = [c_void_p, c_void_p, c_uint, c_void_p, POINTER(c_uint)]
    zkfp.ZKFPM_GetCaptureParamsEx.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int), POINTER(c_int)]
    zkfp.ZKFPM_DBIdentify.argtypes = [c_void_p, c_void_p, c_uint, POINTER(c_uint), POINTER(c_uint)]
    zkfp.ZKFPM_DBAdd.argtypes = [c_void_p, c_uint, c_void_p, c_uint]
    zkfp.ZKFPM_DBMerge.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p, c_void_p, POINTER(c_uint)]
    zkfp.ZKFPM_DBMatch.argtypes = [c_void_p, c_void_p, c_uint, c_void_p, c_uint]


# ====================================
# FINGERPRINT DEVICE INIT
# ====================================
def init_device():
    print("Initializing fingerprint SDK...")
    _set_api()
    if zkfp.ZKFPM_Init() != 0:
        print("Failed to initialize SDK")
        sys.exit(1)

    count = zkfp.ZKFPM_GetDeviceCount()
    print(f"Devices detected: {count}")
    if count <= 0:
        print("No fingerprint device found")
        sys.exit(1)

    handle = zkfp.ZKFPM_OpenDevice(0)
    if handle == 0:
        print("Failed to open fingerprint device")
        sys.exit(1)

    print("Fingerprint device opened successfully")
    global DB_HANDLE, FP_IMG_BUF, FP_IMG_SIZE, DEV_HANDLE
    DEV_HANDLE = handle
    DB_HANDLE = zkfp.ZKFPM_DBInit()
    if not DB_HANDLE:
        print("Failed to initialize fingerprint DB cache")
        sys.exit(1)

    # Prepare image buffer for capture
    width = c_int(0)
    height = c_int(0)
    dpi = c_int(0)
    ret = zkfp.ZKFPM_GetCaptureParamsEx(handle, byref(width), byref(height), byref(dpi))
    if ret != 0 or width.value <= 0 or height.value <= 0:
        print("Failed to get capture params.")
        sys.exit(1)
    FP_IMG_SIZE = width.value * height.value
    FP_IMG_BUF = create_string_buffer(FP_IMG_SIZE)

    _load_fingerprint_db()
    return handle


def _reset_device():
    global DEV_HANDLE, DB_HANDLE, FP_IMG_BUF, FP_IMG_SIZE
    try:
        if DB_HANDLE:
            zkfp.ZKFPM_DBFree(DB_HANDLE)
    except Exception:
        pass
    try:
        if DEV_HANDLE:
            zkfp.ZKFPM_CloseDevice(DEV_HANDLE)
    except Exception:
        pass
    try:
        zkfp.ZKFPM_Terminate()
    except Exception:
        pass
    time.sleep(0.5)
    return init_device()

# ====================================
# CAPTURE FINGERPRINT
# ====================================
def capture_fingerprint(handle):
    template = create_string_buffer(2048)
    template_len = c_uint(2048)

    ret = zkfp.ZKFPM_AcquireFingerprint(handle, FP_IMG_BUF, FP_IMG_SIZE, template, byref(template_len))
    if ret == 0:
        print("Fingerprint captured")
        return template.raw[:template_len.value], template_len.value, ret
    else:
        err = ERR_MAP.get(ret, "UNKNOWN")
        print(f"No fingerprint detected (ret={ret} {err})")
        return None, 0, ret


def _load_fingerprint_db():
    global FID_TO_USER
    if not os.path.isfile(FINGERPRINT_DB_FILE):
        print("Fingerprint DB file not found, starting empty.")
        return

    with open(FINGERPRINT_DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    FID_TO_USER = {}
    for item in data:
        fid = int(item["fid"])
        user_id = str(item["zkteco_user_id"])
        tpl = base64.b64decode(item["template_b64"])
        tpl_buf = create_string_buffer(tpl, len(tpl))
        ret = zkfp.ZKFPM_DBAdd(DB_HANDLE, fid, tpl_buf, len(tpl))
        if ret == 0:
            FID_TO_USER[fid] = user_id
    print(f"Loaded {len(FID_TO_USER)} fingerprint templates into DB cache.")


def _save_fingerprint_db(entries):
    with open(FINGERPRINT_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

# ====================================
# MATCH FINGERPRINT (MOCK)
# ====================================
def match_fingerprint(template_bytes, template_len):
    if not DB_HANDLE:
        return None
    tpl_buf = create_string_buffer(template_bytes, template_len)
    fid = c_uint(0)
    score = c_uint(0)
    ret = zkfp.ZKFPM_DBIdentify(DB_HANDLE, tpl_buf, template_len, byref(fid), byref(score))
    if ret == 0:
        return FID_TO_USER.get(fid.value)
    return None


def enroll_fingerprint(user_id, handle):
    print(f"Enrollment started for user {user_id}. Place the same finger 3 times.")
    captures = []
    while len(captures) < 3:
        print(f"Waiting for capture {len(captures) + 1}/3 (place finger, then lift).")
        try:
            tpl, tpl_len, _ = capture_fingerprint(handle)
            if tpl and tpl_len > 0:
                print(f"Captured raw template (len={tpl_len}).")
                captures.append((tpl, tpl_len))
                print(f"Captured {len(captures)} / 3")
                time.sleep(0.8)
            else:
                time.sleep(0.3)
        except Exception as e:
            print(f"Capture error: {e}")
            time.sleep(0.5)

    reg_tmp = create_string_buffer(2048)
    reg_len = c_uint(2048)
    t1 = create_string_buffer(captures[0][0], captures[0][1])
    t2 = create_string_buffer(captures[1][0], captures[1][1])
    t3 = create_string_buffer(captures[2][0], captures[2][1])
    ret = zkfp.ZKFPM_DBMerge(DB_HANDLE, t1, t2, t3, reg_tmp, byref(reg_len))
    if ret != 0:
        print(f"Enrollment merge failed: {ret}")
        return False

    existing = []
    if os.path.isfile(FINGERPRINT_DB_FILE):
        with open(FINGERPRINT_DB_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    next_fid = 1
    if existing:
        next_fid = max(int(x["fid"]) for x in existing) + 1

    ret = zkfp.ZKFPM_DBAdd(DB_HANDLE, next_fid, reg_tmp, reg_len.value)
    if ret != 0:
        print(f"DB add failed: {ret}")
        return False

    tpl_b64 = base64.b64encode(reg_tmp.raw[: reg_len.value]).decode("ascii")
    existing.append({"fid": next_fid, "zkteco_user_id": str(user_id), "template_b64": tpl_b64})
    _save_fingerprint_db(existing)
    FID_TO_USER[next_fid] = str(user_id)
    print(f"Enrollment successful. fid={next_fid}")
    return True

# ====================================
# MAIN LOOP
# ====================================
def _capture_with_retry(device_handle, attempts=5, delay=0.25):
    last_ret = None
    for _ in range(attempts):
        tpl, tpl_len, ret = capture_fingerprint(device_handle)
        last_ret = ret
        if ret == 0 and tpl:
            return tpl, tpl_len, ret
        time.sleep(delay)
    return None, 0, last_ret if last_ret is not None else -1


def _run_capture_loop(device_handle):
    print("Fingerprint reader ready. Place finger...")
    fail_count = 0
    while True:
        # Slow down capture polling to reduce CAPTURE_FAIL flapping
        time.sleep(0.4)
        template, template_len, ret = _capture_with_retry(device_handle, attempts=4, delay=0.25)
        if template:
            print(f"Captured raw template (len={template_len}).")
            user_id = match_fingerprint(template, template_len)
            print(f"Matched user_id={user_id}")
            if user_id:
                ok, msg = handle_punch(
                    user_id,
                    datetime.now(),
                    DEVICE_ID,
                    raw_payload={"template_len": template_len},
                    source="fingerprint",
                )
                if not ok:
                    print(f"Failed: {msg}")
            else:
                print("No matching fingerprint found in local DB.")
                time.sleep(2)  # Prevent double scan
            fail_count = 0
        else:
            if ret == -8:
                fail_count += 1
                if fail_count >= 20:
                    print("Repeated CAPTURE_FAIL; resetting device...")
                    device_handle = _reset_device()
                    fail_count = 0
        retry_pending()
        time.sleep(0.6)  # Short delay before next scan


def _list_enrolled():
    if not os.path.isfile(FINGERPRINT_DB_FILE):
        print("No enrollments found.")
        return
    with open(FINGERPRINT_DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        print("No enrollments found.")
        return
    print("Enrolled users:")
    for item in data:
        print(f"- fid {item['fid']} -> user {item['zkteco_user_id']}")


def _parse_args():
    parser = argparse.ArgumentParser(description="ZK Fingerprint Middleware")
    sub = parser.add_subparsers(dest="cmd")

    enroll = sub.add_parser("enroll", help="Enroll a user fingerprint")
    enroll.add_argument("--user-id", required=True, help="ZKTeco user ID to enroll")

    sub.add_parser("run", help="Run capture loop (default)")
    sub.add_parser("list", help="List enrolled fingerprints")

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    device_handle = init_device()

    if args.cmd == "enroll":
        enroll_fingerprint(args.user_id, device_handle)
        sys.exit(0)
    if args.cmd == "list":
        _list_enrolled()
        sys.exit(0)

    _run_capture_loop(device_handle)
