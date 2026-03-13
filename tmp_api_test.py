
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao sys.path
root = Path(r"c:\AuditoriaTA\Sistema")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

try:
    from backend.routers.ia import analisar_subitem
    from backend.models import IAAnalyzeRequest
    print("SUCCESS: Imports ok")
except Exception as e:
    import traceback
    print(f"FAILED: Imports failed\n{traceback.format_exc()}")
    sys.exit(1)

# Mock request body
request_body = IAAnalyzeRequest(
    api_key="", # Depender do fallback do banco
    economico=False,
    modo_analise="completo",
    provider="openai"
)

print(f"--- INICIANDO TESTE ANALISAR SUBITEM (ID 69) ---")
try:
    # Simular a chamada ao endpoint
    # Nota: No ambiente real, o FastAPI injeta dependências. 
    # Aqui chamamos diretamente.
    response = analisar_subitem(avaliacao_id=69, body=request_body)
    print(f"RESULT SUCCESS: {response}")
except Exception as e:
    import traceback
    print(f"RESULT FAILED:\n{traceback.format_exc()}")
