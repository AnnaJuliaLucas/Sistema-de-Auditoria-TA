# test_migration.py
import requests
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from backend.db import get_db

def test():
    print("Setting up test data...")
    with get_db() as conn:
        cursor = conn.cursor()
        # Corrupt one item from audit 3
        cursor.execute("UPDATE avaliacoes SET subitem_nome = 'Subitem 1' WHERE auditoria_id = 3 AND subitem_idx = 0")
        conn.commit()
    
    print("Calling migration endpoint...")
    try:
        # Assuming backend is running on localhost:8000
        response = requests.post("http://localhost:8000/api/debug/migrate/subitem-names")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error calling endpoint: {e}")
        print("Falling back to direct function call for verification...")
        from backend.routers.debug import migrate_subitem_names
        res = migrate_subitem_names()
        print(f"Direct result: {res}")

    print("Verifying fix...")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT subitem_nome FROM avaliacoes WHERE auditoria_id = 3 AND subitem_idx = 0")
        name = cursor.fetchone()[0]
        print(f"New name: '{name}'")
        if name != "Subitem 1":
            print("SUCCESS: Name was corrected!")
        else:
            print("FAILURE: Name remains 'Subitem 1'")

if __name__ == "__main__":
    test()
