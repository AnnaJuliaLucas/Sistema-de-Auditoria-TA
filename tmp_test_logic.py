
import sys
from pathlib import Path
import json

root = Path(r"c:\AuditoriaTA\Sistema")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.db import get_avaliacao, get_auditoria, salvar_analise_ia

def test_flow():
    avaliacao_id = 69
    print(f"--- TESTANDO FLUXO COMPLETO PARA ID {avaliacao_id} ---")
    
    # 1. Testar recuperação de dados
    av = get_avaliacao(avaliacao_id)
    if not av:
        print("ERROR: Avaliação não encontrada")
        return
    print(f"DEBUG: Avaliação recuperada: {av['pratica_num']}.{av['subitem_idx']+1}")
    
    aud = get_auditoria(av["auditoria_id"])
    if not aud:
        print("ERROR: Auditoria não encontrada")
        return
    print(f"DEBUG: Auditoria recuperada: {aud['unidade']}")
    
    # 2. Simular Resultado da IA
    mock_result = {
        "decisao": "permanece",
        "nota_sugerida": 4,
        "confianca": "alta",
        "analise_detalhada": "Teste de diagnóstico: tudo parece ok no fluxo de dados.",
        "pontos_atendidos": ["Evidência A verificada", "Evidência B ok"],
        "pontos_faltantes": [],
        "arquivos_analisados": 2,
        "imagens_analisadas": 0
    }
    
    # 3. Testar salvamento
    print("DEBUG: Chamando salvar_analise_ia...")
    try:
        salvar_analise_ia(avaliacao_id, mock_result, av.get("nota_self_assessment", 0))
        print("SUCCESS: salvar_analise_ia executado sem erros.")
    except Exception as e:
        print(f"FAILED: Erro ao salvar: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Verificar se salvou mesmo
    av_after = get_avaliacao(avaliacao_id)
    print(f"VERIFICAÇÃO: ia_decisao no banco = {av_after.get('ia_decisao')}")
    print(f"VERIFICAÇÃO: ia_status no banco = {av_after.get('ia_status')}")

test_flow()
