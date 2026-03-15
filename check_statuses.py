import sqlite3
import os

db_path = r'C:\AuditoriaTA\dados\auditoria_ta.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, unidade, area, status, evidence_folder_path FROM auditorias")
    rows = cursor.fetchall()
    print(f"Total audits: {len(rows)}")
    for row in rows:
        print(f"ID: {row['id']} | Status: '{row['status']}' | Folder: {row['evidence_folder_path']}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
