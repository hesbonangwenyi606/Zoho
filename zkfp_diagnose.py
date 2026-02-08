import os
import sys
import time
from ctypes import *

from dotenv import load_dotenv

load_dotenv()

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


def _resolve_dll_path():
    env_path = os.getenv("ZKFP_DLL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    for name in ("zkfp.dll", "libzkfp.dll"):
        candidate = os.path.join(os.getcwd(), name)
        if os.path.exists(candidate):
            return candidate
    return None


def main():
    dll_path = _resolve_dll_path()
    if not dll_path:
        print("ERROR: zkfp.dll/libzkfp.dll not found. Set ZKFP_DLL_PATH.")
        sys.exit(1)

    zkfp = WinDLL(dll_path)
    print(f"Loaded {os.path.basename(dll_path)}")

    # Function signatures
    zkfp.ZKFPM_Init.restype = c_int
    zkfp.ZKFPM_Terminate.restype = c_int
    zkfp.ZKFPM_GetDeviceCount.restype = c_int
    zkfp.ZKFPM_OpenDevice.restype = c_void_p
    zkfp.ZKFPM_CloseDevice.restype = c_int
    zkfp.ZKFPM_GetCaptureParamsEx.restype = c_int
    zkfp.ZKFPM_AcquireFingerprintImage.restype = c_int
    zkfp.ZKFPM_AcquireFingerprint.restype = c_int

    zkfp.ZKFPM_OpenDevice.argtypes = [c_int]
    zkfp.ZKFPM_CloseDevice.argtypes = [c_void_p]
    zkfp.ZKFPM_GetCaptureParamsEx.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int), POINTER(c_int)]
    zkfp.ZKFPM_AcquireFingerprintImage.argtypes = [c_void_p, c_void_p, c_uint]
    zkfp.ZKFPM_AcquireFingerprint.argtypes = [c_void_p, c_void_p, c_uint, c_void_p, POINTER(c_uint)]

    ret = zkfp.ZKFPM_Init()
    print(f"Init ret={ret} {ERR_MAP.get(ret, '')}")
    if ret != 0:
        return

    count = zkfp.ZKFPM_GetDeviceCount()
    print(f"Device count={count}")
    if count <= 0:
        zkfp.ZKFPM_Terminate()
        return

    hdev = zkfp.ZKFPM_OpenDevice(0)
    if not hdev:
        print("OpenDevice failed")
        zkfp.ZKFPM_Terminate()
        return

    width = c_int(0)
    height = c_int(0)
    dpi = c_int(0)
    ret = zkfp.ZKFPM_GetCaptureParamsEx(hdev, byref(width), byref(height), byref(dpi))
    print(f"GetCaptureParamsEx ret={ret} {ERR_MAP.get(ret, '')} width={width.value} height={height.value} dpi={dpi.value}")
    if ret != 0 or width.value <= 0 or height.value <= 0:
        zkfp.ZKFPM_CloseDevice(hdev)
        zkfp.ZKFPM_Terminate()
        return

    img_size = width.value * height.value
    img_buf = create_string_buffer(img_size)

    print("Testing AcquireFingerprintImage (5 attempts)...")
    for i in range(5):
        ret = zkfp.ZKFPM_AcquireFingerprintImage(hdev, img_buf, img_size)
        print(f"Image capture {i+1}: ret={ret} {ERR_MAP.get(ret, '')}")
        time.sleep(0.6)

    print("Testing AcquireFingerprint + template (5 attempts)...")
    for i in range(5):
        tpl = create_string_buffer(2048)
        tpl_len = c_uint(2048)
        ret = zkfp.ZKFPM_AcquireFingerprint(hdev, img_buf, img_size, tpl, byref(tpl_len))
        msg = ERR_MAP.get(ret, "")
        print(f"Template capture {i+1}: ret={ret} {msg} tpl_len={tpl_len.value if ret == 0 else 0}")
        time.sleep(0.6)

    zkfp.ZKFPM_CloseDevice(hdev)
    zkfp.ZKFPM_Terminate()


if __name__ == "__main__":
    main()
