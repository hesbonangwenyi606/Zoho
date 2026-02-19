# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import middleware_fingerprint as mf  # your existing middleware file

app = FastAPI(title="Zoho Attendance Live Server")

class PunchData(BaseModel):
    Worker_ID: str
    timestamp: str  # ISO format: 2026-02-10T10:00:00
    device_id: str
    raw_payload: dict = None
    source: str = None

@app.post("/punch")
async def record_punch(punch: PunchData):
    try:
        ts = datetime.fromisoformat(punch.timestamp)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")

    ok, msg = mf.handle_punch(
        Worker_ID=punch.Worker_ID,
        timestamp=ts,
        device_id=punch.device_id,
        raw_payload=punch.raw_payload,
        source=punch.source,
    )
    return {"success": ok, "message": msg}

@app.get("/retry_pending")
async def retry_pending():
    success, fail = mf.retry_pending()
    return {"retried_success": success, "retried_fail": fail}
