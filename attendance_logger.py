import json
from datetime import datetime
import os

# Path to my attendance JSON file
ATTENDANCE_FILE = "attendance.json"

def mark_attendance(worker_id, worker_name):
    """
    Automatically records fingerprint sign-in for a worker.
    """
    # Ensure file exists
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w") as f:
            json.dump([], f)

    # Load existing attendance
    with open(ATTENDANCE_FILE, "r") as f:
        attendance_list = json.load(f)

    # Check if worker already signed in today
    today_str = datetime.now().date().isoformat()
    already_signed_in = any(
        record["Worker_ID"] == worker_id and record["Time_In"].startswith(today_str)
        for record in attendance_list
    )

    if already_signed_in:
        print(f"Worker {worker_name} already signed in today.")
        return

    # Create new attendance record
    attendance_record = {
        "Worker_ID": worker_id,
        "Worker_Name": worker_name,
        "Time_In": datetime.now().isoformat()
    }

    # Append and save
    attendance_list.append(attendance_record)
    with open(ATTENDANCE_FILE, "w") as f:
        json.dump(attendance_list, f, indent=2)

    print(f"✅ Attendance marked for {worker_name} at {attendance_record['Time_In']}")
