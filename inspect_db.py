import sqlite3
import pandas as pd
from pathlib import Path

db_path = r"C:\AuditoriaTA\dados\auditoria_ta.db"
if not Path(db_path).exists():
    print(f"Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
print("Latest 5 Audits:")
auds = pd.read_sql_query("SELECT id, unidade, area, ciclo, data_criacao FROM auditorias ORDER BY id DESC LIMIT 5", conn)
print(auds)

if not auds.empty:
    latest_id = auds.iloc[0]['id']
    print(f"\nSubitems for Latest Audit (ID={latest_id}):")
    avals = pd.read_sql_query(f"SELECT pratica_num, subitem_idx, subitem_nome, nota_self_assessment FROM avaliacoes WHERE auditoria_id={latest_id} ORDER BY pratica_num, subitem_idx", conn)
    print(avals.head(20))
    
    total_zero = (avals['nota_self_assessment'] == 0).sum()
    total_null = avals['nota_self_assessment'].isna().sum()
    print(f"\nSummary for ID={latest_id}: Total={len(avals)}, Zero={total_zero}, NULL={total_null}")

conn.close()
