import sqlite3
import os

db_path = r'C:\AuditoriaTA\dados\auditoria_ta.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", tables)
        
        cursor.execute("PRAGMA table_info(auditorias)")
        cols = cursor.fetchall()
        print("Columns in auditorias:", [c[1] for c in cols])

        cursor.execute("SELECT id, unidade, area, ciclo, status FROM auditorias")
        rows = cursor.fetchall()
        print("Auditorias count:", len(rows))
        for row in rows:
            print(f"Audit {row[0]}: {row[1]} - {row[2]} ({row[3]}) - Status: {row[4]}")
            cursor.execute("SELECT COUNT(*) FROM avaliacoes WHERE auditoria_id=?", (row[0],))
            total_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM avaliacoes WHERE auditoria_id=? AND nota_self_assessment IS NOT NULL", (row[0],))
            sa_count = cursor.fetchone()[0]
            print(f"  Evaluations: {total_count} (SA Notes: {sa_count})")
        cursor.execute("SELECT COUNT(*) FROM avaliacoes WHERE auditoria_id NOT IN (SELECT id FROM auditorias)")
        orphaned_count = cursor.fetchone()[0]
        print(f"\nOrphaned evaluations (not linked to any audit): {orphaned_count}")
        
        if orphaned_count > 0:
            cursor.execute("SELECT DISTINCT auditoria_id FROM avaliacoes WHERE auditoria_id NOT IN (SELECT id FROM auditorias)")
            orphaned_ids = cursor.fetchall()
            print(f"Orphaned Auditoria IDs: {[r[0] for r in orphaned_ids]}")
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()
