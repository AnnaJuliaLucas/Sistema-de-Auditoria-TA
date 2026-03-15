import sqlite3
import openpyxl
import os

db_path = r'C:\AuditoriaTA\dados\auditoria_ta.db'
excel_path = r"C:\Users\Duda PC\OneDrive\Documentos\Automateasy\Auditoria\Self Assessment\Juiz de Fora\Assessment Automação 2026_AMJF_Redução.xlsx"
audit_id = 3

def safe_int(val):
    if val is None: return 0
    try:
        return int(float(str(val).replace(',', '.')))
    except:
        return 0

if not os.path.exists(excel_path):
    print(f"Excel not found: {excel_path}")
    exit(1)

wb = openpyxl.load_workbook(excel_path, data_only=True)
ws = wb.active

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Updating Audit {audit_id} scores...")

current_p_num = None
s_idx = 0
updated_count = 0

for i, row in enumerate(ws.iter_rows(values_only=True)):
    # row[0] = N, row[1] = Prática, row[2] = Evidência, row[8] = Nota
    
    if row[0] and str(row[0]).strip().isdigit():
        current_p_num = int(row[0])
        s_idx = 0
        print(f"Practice {current_p_num} found on row {i+1}")
    
    # Check if this row is a subitem (Column C/index 2 has content)
    if current_p_num is not None and row[2]:
        # Skip header rows
        if str(row[2]).strip().upper() == "EVIDÊNCIA" or str(row[1]).strip().upper() == "PRÁTICA":
            continue
            
        nota = safe_int(row[8])
        
        # Only update if it's within practice range (simplified, just update based on s_idx)
        # In this audit, Conhecimento is Practice 4
        if current_p_num == 4:
             print(f"Row {i+1}: P{current_p_num} S{s_idx} -> Nota {nota}")
             
        cursor.execute("""
            UPDATE avaliacoes 
            SET nota_self_assessment = ? 
            WHERE auditoria_id = ? AND pratica_num = ? AND subitem_idx = ?
        """, (nota, audit_id, current_p_num, s_idx))
        
        if cursor.rowcount > 0:
            updated_count += 1
        s_idx += 1

conn.commit()
print(f"Finished. Total rows updated in DB: {updated_count}")
conn.close()
