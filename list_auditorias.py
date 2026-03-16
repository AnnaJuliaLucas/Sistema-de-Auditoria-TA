# list_auditorias.py
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from backend.db import get_db

def list_all():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, unidade, area, ciclo FROM auditorias")
        rows = cursor.fetchall()
        print(f"Total Auditorias: {len(rows)}")
        for row in rows:
            print(f"ID: {row[0]} | {row[1]} - {row[2]} ({row[3]})")

if __name__ == "__main__":
    list_all()
