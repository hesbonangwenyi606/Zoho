import time
from datetime import datetime

from middleware_core import handle_punch, retry_pending

# --- Simulation of ZKTeco logs (for testing only) ---
if __name__ == "__main__":
    print("=== ZKTeco Middleware Simulator ===")

    # Example: simulate a few scans
    handle_punch("1001", datetime.now(), "ZKTeco_9500_10R", raw_payload={"sim": "data"}, source="sim")
    time.sleep(1)
    handle_punch("1002", datetime.now(), "ZKTeco_9500_10R", raw_payload={"sim": "data"}, source="sim")

    # Try pushing pending records
    retry_pending()
