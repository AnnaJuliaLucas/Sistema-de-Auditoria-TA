import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from backend.db import get_auditoria, listar_auditorias

# Mock what serve_file does
def test_detection(path_str):
    file_path = Path(path_str)
    parts = file_path.parts
    audit_id = None
    
    print(f"Testing detection for: {path_str}")
    
    if "uploads" in parts:
        idx = parts.index("uploads")
        audit_id = int(parts[idx+1])
        print(f"  Found via 'uploads': ID {audit_id}")
    else:
        # Robust detection
        all_audits = listar_auditorias()
        path_str_norm = str(file_path.absolute()).lower().replace("\\", "/")
        for a in all_audits:
            fp = a.get("evidence_folder_path")
            if fp:
                fp_norm = str(Path(fp).absolute()).lower().replace("\\", "/")
                if path_str_norm.startswith(fp_norm):
                    audit_id = a["id"]
                    print(f"  Found via robust detection: ID {audit_id} (folder: {fp})")
                    break
    
    if audit_id:
        aud = get_auditoria(audit_id)
        status_raw = aud.get("status")
        status_norm = str(status_raw or "").lower().strip().replace(" ", "_")
        print(f"  Audit ID: {audit_id}")
        print(f"  Raw Status: '{status_raw}'")
        print(f"  Norm Status: '{status_norm}'")
        if status_norm == "em_andamento":
            print("  RESULT: ACCESS GRANTED")
        else:
            print(f"  RESULT: ACCESS DENIED (Status '{status_norm}' != 'em_andamento')")
    else:
        print("  RESULT: AUDIT NOT FOUND")

# Test cases
test_detection(r"C:/Users/Duda PC/OneDrive/Documentos/Automateasy/Auditoria/Evidências/Juiz de Fora/Redução/1 - ROTINAS DE TA/1.1 - Backup periódico e por evento/Atualizado texto longo.PNG")
print("-" * 20)
# Test with a capitalized case
test_detection(r"C:/Users/Duda PC/OneDrive/Documentos/Automateasy/Auditoria/Evidências/Juiz de Fora/Redução/Test.PDF")
