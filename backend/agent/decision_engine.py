"""
decision_engine.py — Motor de decisão autônomo do Agente de Auditoria.

Orquestra a análise de evidências para subitens de uma auditoria,
reutilizando o AuditAIAnalyzer existente e o mapeamento de evidências.
"""

import os
import sys
import json
import time
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

log = logging.getLogger("agente_decision_engine")

# Ensure parent modules are importable
_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)


def _resolve_api_key(body_key: str, audit: dict) -> str:
    """Resolve API key from: request body → audit config → system config → env."""
    if body_key:
        return body_key
    key = audit.get("openai_api_key", "")
    if key:
        log.info(f"Resolved API Key from Audit: {key[:5]}...")
        return key
    try:
        from backend.db import get_system_config
        config_key = get_system_config("openai_api_key")
        if config_key:
            log.info("Resolved API Key from System Config")
            return config_key
    except Exception:
        pass
    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key:
        log.info("Resolved API Key from Environment")
    return env_key


def _resolve_provider(body_provider: str, audit: dict) -> str:
    """Resolve LLM provider from: request body → audit config → system config."""
    if body_provider:
        return body_provider
    provider = audit.get("ai_provider", "")
    if provider:
        log.info(f"Resolved Provider from Audit: {provider}")
        return provider
    try:
        from backend.db import get_system_config
        global_p = get_system_config("ai_provider", "openai")
        log.info(f"Resolved Provider from Global Config: {global_p}")
        return global_p
    except Exception:
        log.warning("Failed to get global ai_provider, defaulting to openai")
        return "openai"


def _resolve_base_url(body_url: Optional[str], audit: dict) -> str:
    """Resolve base URL from: request body → audit config → system config."""
    if body_url:
        return body_url
    url = audit.get("ai_base_url", "")
    if url:
        return url
    try:
        from backend.db import get_system_config
        return get_system_config("ai_base_url", "")
    except Exception:
        return ""


def _ensure_evidence_folder(audit: dict) -> str:
    """
    Ensure the evidence folder exists.
    If folder is missing but evidence_zip_url is set, trigger lazy restoration.
    Returns the usable evidence folder path (possibly restored).
    """
    from backend.routers.evidencias import resolve_and_ensure_path, extract_zip_robustly
    from backend.db import BASE_DIR
    import urllib.request
    import shutil

    ev_folder = audit.get("evidence_folder_path", "")
    audit_id = audit.get("id")

    if ev_folder and Path(ev_folder).is_dir():
        return ev_folder

    # Try the server-internal uploads path
    server_base = BASE_DIR / "uploads" / str(audit_id) / "evidences"
    if server_base.is_dir():
        return str(server_base)

    # Lazy restore from ZIP URL
    zip_url = audit.get("evidence_zip_url", "")
    if zip_url:
        zip_path = BASE_DIR / "uploads" / str(audit_id) / f"evidences_{audit_id}.zip"
        try:
            log.info(f"Agent: Restoring audit {audit_id} evidence from {zip_url}...")
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            if zip_url.startswith("http"):
                urllib.request.urlretrieve(zip_url, zip_path)
            elif os.path.exists(zip_url):
                shutil.copy2(zip_url, zip_path)
            extract_zip_robustly(zip_path, server_base)
            log.info(f"Agent: Evidence restored to {server_base}")
            return str(server_base)
        except Exception as e:
            log.error(f"Agent: Evidence restoration failed: {e}")

    return ev_folder  # May be empty — caller handles the error


def analyze_single_subitem(
    audit: dict,
    avaliacao: dict,
    api_key: str = "",
    provider: str = "",
    base_url: Optional[str] = None,
    economico: bool = False,
) -> Dict[str, Any]:
    """
    Analyze a single subitem's evidence against Self Assessment score.

    Args:
        audit: Full audit dict from DB (with evidence_folder_path, etc.)
        avaliacao: Full avaliacao dict from DB (with pratica_num, subitem_idx, etc.)
        api_key: Optional override for LLM API key.
        provider: Optional override for LLM provider (openai/anthropic/gemini/ollama).
        base_url: Optional override for LLM base URL.
        economico: Use economic (cheaper/faster) mode.

    Returns:
        dict with analysis result (decisao, nota_sugerida, analise_detalhada, etc.)
    """
    from ai_analyzer import AuditAIAnalyzer, build_evidence_map
    from backend.db import salvar_analise_ia

    t0 = time.time()

    # 1. Resolve config
    resolved_key = _resolve_api_key(api_key, audit)
    resolved_provider = _resolve_provider(provider, audit)
    resolved_url = _resolve_base_url(base_url, audit)

    log.info(f"Agent Engine: Resolving for practice {avaliacao.get('pratica_num')} subitem {avaliacao.get('subitem_idx')}")
    log.info(f" > Provider: {resolved_provider}")
    log.info(f" > Key present: {bool(resolved_key)}")
    log.info(f" > Custom URL: {resolved_url}")

    # Permitir chave vazia se for Ollama, Agente Interno ou se houver uma Base URL custom
    needs_key = resolved_provider not in ("ollama", "interno") and not resolved_url
    if needs_key and not resolved_key:
        log.error(f"Agent Engine: Blocked due to missing API Key for provider {resolved_provider}")
        return {
            "erro": "API Key não configurada. Configure na auditoria ou globalmente.",
            "status": "error",
        }

    # 2. Ensure evidence folder exists (lazy restore if needed)
    ev_folder = _ensure_evidence_folder(audit)
    if not ev_folder or not Path(ev_folder).is_dir():
        return {
            "erro": f"Pasta de evidências não encontrada: {ev_folder}",
            "status": "error",
        }

    # 3. Build evidence map and find files for this subitem
    evidence_map = build_evidence_map(ev_folder)
    key = (avaliacao["pratica_num"], avaliacao["subitem_idx"])
    evidence_files = evidence_map.get(key, [])
    log.info(f"Agent: Subitem {key} → {len(evidence_files)} evidence files")

    # 4. Set up analyzer
    modo_analise = audit.get("modo_analise", "completo")
    if modo_analise == "economico":
        economico = True

    if resolved_provider == "interno":
        from backend.agent.internal_analyzer import InternalHeuristicAnalyzer
        analyzer = InternalHeuristicAnalyzer()
    else:
        analyzer = AuditAIAnalyzer(
            api_key=resolved_key,
            economico=economico,
            provider=resolved_provider,
            base_url=resolved_url if resolved_url else None,
        )

    # 5. Run analysis
    nota_sa = avaliacao.get("nota_self_assessment", 0) or 0
    result = analyzer.analyze_subitem(
        pratica_num=avaliacao["pratica_num"],
        subitem_idx=avaliacao["subitem_idx"],
        pratica_nome=avaliacao.get("pratica_nome", ""),
        subitem_nome=avaliacao.get("subitem_nome", ""),
        evidencia_descricao=avaliacao.get("evidencia_descricao", "") or "",
        niveis_planilha={i: avaliacao.get(f"nivel_{i}", "") for i in range(5)},
        nota_self_assessment=nota_sa,
        evidence_files=[str(f) for f in evidence_files],
    )

    # 6. Save to DB
    salvar_analise_ia(avaliacao["id"], result, nota_sa)

    elapsed = round(time.time() - t0, 1)
    result["duracao_segundos"] = elapsed
    result["avaliacao_id"] = avaliacao["id"]
    log.info(
        f"Agent: Subitem {key} analyzed in {elapsed}s → "
        f"decisao={result.get('decisao')}, nota={result.get('nota_sugerida')}"
    )

    return result


def analyze_all_pending(
    audit: dict,
    avaliacoes: List[dict],
    api_key: str = "",
    provider: str = "",
    base_url: Optional[str] = None,
    economico: bool = False,
    on_progress=None,
) -> Dict[str, Any]:
    """
    Analyze all pending subitems for an audit, one by one.

    Args:
        audit: Full audit dict from DB.
        avaliacoes: List of avaliacao dicts (all subitems for this audit).
        on_progress: Optional callback(current, total, avaliacao_id, result) for progress tracking.

    Returns:
        dict with batch results summary.
    """
    pending = [
        av for av in avaliacoes
        if (av.get("ia_status") or "") != "ok"
    ]

    total = len(pending)
    results = []
    errors = []

    for idx, av in enumerate(pending, 1):
        try:
            if on_progress:
                on_progress(idx, total, av["id"], None)

            result = analyze_single_subitem(
                audit=audit,
                avaliacao=av,
                api_key=api_key,
                provider=provider,
                base_url=base_url,
                economico=economico,
            )

            if result.get("status") == "error":
                errors.append({"avaliacao_id": av["id"], "erro": result.get("erro", "")})
            else:
                results.append({
                    "avaliacao_id": av["id"],
                    "pratica_num": av["pratica_num"],
                    "subitem_idx": av["subitem_idx"],
                    "decisao": result.get("decisao"),
                    "nota_sugerida": result.get("nota_sugerida"),
                    "duracao_segundos": result.get("duracao_segundos"),
                })

            if on_progress:
                on_progress(idx, total, av["id"], result)

        except Exception as e:
            log.error(f"Agent: Error analyzing avaliacao {av['id']}: {e}")
            errors.append({
                "avaliacao_id": av["id"],
                "erro": str(e),
                "trace": traceback.format_exc()[-300:],
            })

    return {
        "total_pendentes": total,
        "analisados": len(results),
        "erros": len(errors),
        "resultados": results,
        "detalhes_erros": errors,
    }

def analyze_selection(
    audit: dict,
    avaliacoes: List[dict],
    selected_ids: List[int],
    api_key: str = "",
    provider: str = "",
    base_url: Optional[str] = None,
    economico: bool = False,
    on_progress=None,
) -> Dict[str, Any]:
    """
    Analyze a specific selection of subitems.
    """
    selection = [
        av for av in avaliacoes
        if av["id"] in selected_ids
    ]
    
    total = len(selection)
    results = []
    errors = []

    for idx, av in enumerate(selection, 1):
        try:
            if on_progress:
                on_progress(idx, total, av["id"], None)

            result = analyze_single_subitem(
                audit=audit,
                avaliacao=av,
                api_key=api_key,
                provider=provider,
                base_url=base_url,
                economico=economico,
            )

            if result.get("status") == "error":
                errors.append({"avaliacao_id": av["id"], "erro": result.get("erro", "")})
            else:
                results.append({
                    "avaliacao_id": av["id"],
                    "pratica_num": av["pratica_num"],
                    "subitem_idx": av["subitem_idx"],
                    "decisao": result.get("decisao"),
                    "nota_sugerida": result.get("nota_sugerida"),
                    "duracao_segundos": result.get("duracao_segundos"),
                })

            if on_progress:
                on_progress(idx, total, av["id"], result)

        except Exception as e:
            log.error(f"Agent: Error analyzing avaliacao {av['id']}: {e}")
            errors.append({
                "avaliacao_id": av["id"],
                "erro": str(e),
                "trace": traceback.format_exc()[-300:],
            })

    return {
        "total_selecionados": total,
        "analisados": len(results),
        "erros": len(errors),
        "resultados": results,
        "detalhes_erros": errors,
    }
