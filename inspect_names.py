# inspect_names.py
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from backend.db import get_db, USE_POSTGRES

def inspect():
    with get_db() as conn:
        cursor = conn.cursor()
        print(f"Postgres: {USE_POSTGRES}")
        
        # Check audit 3 specifically
        cursor.execute("SELECT id, pratica_num, subitem_idx, subitem_nome FROM avaliacoes WHERE auditoria_id = 3 LIMIT 10")
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | P: {row[1]} | S: {row[2]} | Name: '{row[3]}'")

if __name__ == "__main__":
    inspect()
