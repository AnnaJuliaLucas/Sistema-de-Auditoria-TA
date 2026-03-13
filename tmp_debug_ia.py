import sys
import os
from pathlib import Path

# Setup paths
sys.path.insert(0, r"c:\AuditoriaTA\Sistema")

from backend.db import get_avaliacao, get_auditoria
from ai_analyzer import AuditAIAnalyzer, build_evidence_map

def test_analysis(avaliacao_id):
    try:
        print(f"Testing Avaliacao ID: {avaliacao_id}")
        av = get_avaliacao(avaliacao_id)
        if not av:
            print("Avaliacao not found")
            return
            
        aud = get_auditoria(av["auditoria_id"])
        ev_folder = aud.get("evidence_folder_path", "")
        print(f"Folder: {ev_folder}")
        
        evidence_map = build_evidence_map(ev_folder)
        key = (av["pratica_num"], av["subitem_idx"])
        evidence_files = [str(f) for f in evidence_map.get(key, [])]
        print(f"Evidence files: {len(evidence_files)}")
        
        # Test basic instantiation with Ollama
        analyzer = AuditAIAnalyzer(api_key="sk-test", provider="ollama", economico=True)
        print("Analyzer instantiated (Ollama)")
        
        # Test real client creation (this might fail if openai is missing)
        try:
            client = analyzer._get_client()
            print(f"Client created: {type(client)}")
        except Exception as e:
            print(f"Client creation FAILED: {e}")
            raise
        
        # Now mock only the call itself to see if it reaches it
        from unittest.mock import MagicMock
        if analyzer.provider == "openai":
            analyzer._get_client = MagicMock(return_value=MagicMock())
            analyzer._get_client().chat.completions.create = MagicMock(side_effect=Exception("API Error Mock"))
        
        print("Calling analyze_subitem...")
        try:
            result = analyzer.analyze_subitem(
                pratica_num=av["pratica_num"],
                subitem_idx=av["subitem_idx"],
                pratica_nome=av["pratica_nome"] or "",
                subitem_nome=av["subitem_nome"] or "",
                evidencia_descricao=av.get("evidencia_descricao", "") or "",
                niveis_planilha={},
                nota_self_assessment=av.get("nota_self_assessment", 0) or 0,
                evidence_files=evidence_files,
            )
        except Exception as e:
            print(f"analyze_subitem Call FAILED: {e}")
            raise
        print(f"RESULT SUCCESS: {result.get('decisao')}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analysis(69)
