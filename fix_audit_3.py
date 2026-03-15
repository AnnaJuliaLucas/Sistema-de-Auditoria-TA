import sys
import os

# Add project root to sys.path to allow imports
sys.path.append(os.getcwd())

# Import the necessary functions
from backend.routers.export import importar_assessment
from backend.db import get_auditoria

# Check if audit 3 exists and has a file path
aud = get_auditoria(3)
if not aud:
    print("Audit 3 not found in database.")
    sys.exit(1)

path = aud.get('assessment_file_path')
if not path or not os.path.exists(path):
    print(f"Assessment file not found for Audit 3: {path}")
    # Try the path provided by the user if the one in DB is wrong
    path_user = r"C:\Users\Duda PC\OneDrive\Documentos\Automateasy\Auditoria\Self Assessment\Juiz de Fora\Assessment Automação 2026_AMJF_Redução.xlsx"
    if os.path.exists(path_user):
        print(f"Using user provided path: {path_user}")
        # We might need to update the DB first or just run the import logic manually
        import sqlite3
        from backend.db import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("UPDATE auditorias SET assessment_file_path=? WHERE id=3", (path_user,))
        conn.commit()
        conn.close()
    else:
        print("User provided path also not found.")
        sys.exit(1)

try:
    print(f"Starting re-import for audit 3 using file: {path or path_user}")
    result = importar_assessment(3)
    print(f"Result: {result}")
except Exception as e:
    import traceback
    print(f"Error during import: {e}")
    traceback.print_exc()
