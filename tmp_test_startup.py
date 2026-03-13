
import sys
from pathlib import Path

# Simular o ambiente do uvicorn
root = Path(r"c:\AuditoriaTA\Sistema")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

print("DEBUG: Entrando no teste de startup...")
try:
    from backend.db import init_db
    print("DEBUG: Chamando init_db()...")
    init_db()
    print("DEBUG: init_db() concluído com sucesso!")
except Exception as e:
    import traceback
    print(f"FAILED: Erro no init_db()\n{traceback.format_exc()}")

try:
    from backend.main import app
    print("DEBUG: App instanciado com sucesso!")
except Exception as e:
    import traceback
    print(f"FAILED: Erro ao instanciar o app\n{traceback.format_exc()}")
