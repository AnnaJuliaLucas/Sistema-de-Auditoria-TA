"""
routers/ia.py — AI analysis endpoints.
"""
from fastapi import APIRouter, HTTPException
from backend.db import get_auditoria, get_avaliacao, salvar_analise_ia, get_system_config
from backend.models import IAAnalyzeRequest
import sys
import os
from pathlib import Path
import traceback

# Add parent dir to import ai_analyzer and criterios_oficiais
_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api/ia", tags=["ia"])


@router.post("/analisar/{avaliacao_id}")
def analisar_subitem(avaliacao_id: int, body: IAAnalyzeRequest):
    """Run AI analysis on a single subitem."""
    print(f"--- DEBUG AI: Iniciando análise do subitem {avaliacao_id} ---")
    
    try:
        # 1. Recuperar dados básicos
        av = get_avaliacao(avaliacao_id)
        if not av:
            print(f"ERROR: Avaliação {avaliacao_id} não encontrada")
            raise HTTPException(status_code=404, detail="Avaliação não encontrada")

        aud = get_auditoria(av["auditoria_id"])
        if not aud:
            print(f"ERROR: Auditoria {av['auditoria_id']} não encontrada")
            raise HTTPException(status_code=404, detail="Auditoria não encontrada")

        # 2. Determinar Provider (antes da key, pois Ollama não precisa de API Key)
        provider = body.provider or aud.get("ai_provider") or get_system_config("ai_provider", "openai")
        base_url = body.base_url or aud.get("ai_base_url") or get_system_config("ai_base_url", "")
        
        # 3. Determinar API Key (não obrigatória para Ollama)
        api_key = body.api_key or aud.get("openai_api_key", "")
        if not api_key:
            config_key = get_system_config("openai_api_key")
            if config_key:
                api_key = config_key
            else:
                api_key = os.environ.get("OPENAI_API_KEY", "")

        if not api_key and provider != "ollama":
            print("ERROR: API Key não encontrada em nenhum lugar.")
            audit_id = av["auditoria_id"]
            raise HTTPException(
                status_code=400, 
                detail=f"Chave API OpenAI não configurada. Configure na auditoria (ID {audit_id}) ou globalmente."
            )

        # 3. Preparar evidências
        ev_folder = aud.get("evidence_folder_path", "")
        print(f"DEBUG: Pasta de evidências: {ev_folder}")
        if not ev_folder:
            raise HTTPException(status_code=400, detail="Pasta de evidências não configurada")

        from ai_analyzer import AuditAIAnalyzer, build_evidence_map

        evidence_map = build_evidence_map(ev_folder)
        key = (av["pratica_num"], av["subitem_idx"])
        evidence_files = evidence_map.get(key, [])
        print(f"DEBUG: Chave subitem: {key}, Arquivos encontrados: {len(evidence_files)}")
        
        # 4. Configurar Analyzer
        # Modo de análise
        economico = body.economico
        if body.modo_analise:
            economico = (body.modo_analise == "economico")
        
        if provider == "interno":
            from backend.agent.internal_analyzer import InternalHeuristicAnalyzer
            analyzer = InternalHeuristicAnalyzer()
        else:
            analyzer = AuditAIAnalyzer(
                api_key=api_key, 
                economico=economico,
                provider=provider, 
                base_url=base_url if base_url else None
            )
        
        # 5. Executar Análise
        print(f"DEBUG: Chamando analyzer.analyze_subitem (provider={provider})...")
        result = analyzer.analyze_subitem(
            pratica_num=av["pratica_num"],
            subitem_idx=av["subitem_idx"],
            pratica_nome=av["pratica_nome"],
            subitem_nome=av["subitem_nome"],
            evidencia_descricao=av.get("evidencia_descricao", "") or "",
            niveis_planilha={i: av.get(f"nivel_{i}", "") for i in range(5)},
            nota_self_assessment=av.get("nota_self_assessment", 0) or 0,
            evidence_files=[str(f) for f in evidence_files],
        )
        print(f"DEBUG: Resultado AI recebido: {result.get('decisao')} - Nota: {result.get('nota_sugerida')}")

        # 6. Salvar no banco
        print(f"DEBUG: Tentando salvar resultado no banco para ID {avaliacao_id}...")
        salvar_analise_ia(avaliacao_id, result, av.get("nota_self_assessment", 0))
        print(f"DEBUG: Resultado salvo com sucesso no banco para ID {avaliacao_id}")

        return {
            "ok": True,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        err_trace = traceback.format_exc()
        print(f"CRITICAL ERROR IA:\n{err_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro na análise IA: {str(e)} | TRACE: {err_trace[-300:]}"
        )
