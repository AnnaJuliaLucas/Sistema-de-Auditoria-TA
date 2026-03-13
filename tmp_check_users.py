import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\AuditoriaTA\dados\auditoria_ta.db")

def check_users():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("ERROR: Table 'users' does not exist.")
            return
        
        users = conn.execute("SELECT id, email, role FROM users").fetchall()
        if not users:
            print("INFO: No users found in the 'users' table.")
        else:
            print(f"SUCCESS: Found {len(users)} users:")
            for u in users:
                print(f" - ID: {u['id']}, Email: {u['email']}, Role: {u['role']}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_users()
