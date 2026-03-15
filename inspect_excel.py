import openpyxl
import os

path = r"C:\Users\Duda PC\OneDrive\Documentos\Automateasy\Auditoria\Self Assessment\Juiz de Fora\Assessment Automação 2026_AMJF_Redução.xlsx"

if not os.path.exists(path):
    print(f"File not found: {path}")
else:
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        print(f"Sheet: {ws.title}")
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i > 50: break
            print(f"Row {i+1}: {row[:10]}")
    except Exception as e:
        print(f"Error: {e}")
