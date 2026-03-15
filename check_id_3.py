import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from backend.db import get_auditoria

def check_id_3():
    aud = get_auditoria(3)
    if not aud:
        print("Audit ID 3 not found.")
        return
    print(f"ID: {aud['id']}")
    print(f"Unidade: {aud['unidade']}")
    print(f"Status: {aud['status']}")
    print(f"Folder DB: {aud.get('evidence_folder_path')}")
    print(f"ZIP URL: {aud.get('evidence_zip_url')}")
    print(f"Map head: {str(aud.get('evidence_map'))[:200]}...")

if __name__ == "__main__":
    check_id_3()
