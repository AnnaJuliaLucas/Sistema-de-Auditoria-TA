
import requests
import json
import time

URL = "http://localhost:8000/api/ia/analisar/69"
payload = {
    "api_key": "", # Fallback
    "economico": False,
    "modo_analise": "completo",
    "provider": "openai"
}

print(f"--- TESTANDO ENDPOINT IA (ID 69) ---")
start = time.time()
try:
    r = requests.post(URL, json=payload, timeout=120)
    elapsed = time.time() - start
    print(f"STATUS: {r.status_code} (em {elapsed:.1f}s)")
    try:
        data = r.json()
        print(f"RESPONSE JSON: {json.dumps(data, indent=2)}")
    except:
        print(f"RESPONSE RAW: {r.text[:500]}")
except Exception as e:
    print(f"ERRO NA REQUISIÇÃO: {e}")
