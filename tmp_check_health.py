
import requests
try:
    r = requests.get("http://localhost:8000/api/health", timeout=2)
    print(f"HEALTH STATUS: {r.status_code}")
    print(f"RESPONSE: {r.json()}")
except Exception as e:
    print(f"HEALTH FAILED: {e}")
