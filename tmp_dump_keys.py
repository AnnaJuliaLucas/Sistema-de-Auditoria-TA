
import sys
from pathlib import Path

root = Path(r"c:\AuditoriaTA\Sistema")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.db import get_db

with get_db() as conn:
    # 1. Check system config
    res = conn.execute("SELECT value FROM system_config WHERE key='openai_api_key'").fetchone()
    print(f"CONFIG KEY: {'SET' if res and res['value'] else 'MISSING'}")
    
    # 2. Check audits
    audits = conn.execute("SELECT id, unidade, openai_api_key FROM auditorias").fetchall()
    for a in audits:
        print(f"AUDIT {a['id']} ({a['unidade']}): {'SET' if a['openai_api_key'] else 'MISSING'}")

    # 3. Check for evidence folder
    folder = conn.execute("SELECT evidence_folder_path FROM auditorias WHERE id=(SELECT auditoria_id FROM avaliacoes WHERE id=69)").fetchone()
    print(f"EVIDENCE FOLDER for ID 69: {folder['evidence_folder_path'] if folder else 'NONE'}")
