"""
routers/agente.py — Autonomous Audit Agent API.

Provides endpoints for autonomous analysis of audit subitems.
The agent uses evidence files already associated with the audit
(evidence_folder_path / evidence_zip_url) submitted during audit creation.

Analysis runs asynchronously via background threads. Clients poll
/status/{job_id} until completion.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json
import time
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

log = logging.getLogger("agente_api")
router = APIRouter(prefix="/api/agente", tags=["agente"])

# Thread pool for background analysis jobs
_executor = ThreadPoolExecutor(max_workers=2)


# ─── Request / Response Models ────────────────────────────────────────────────

class AgentAnalyzeRequest(BaseModel):
    api_key: str = ""
    provider: str = ""
    base_url: str = ""
    economico: bool = False

class AgentSelectionRequest(AgentAnalyzeRequest):
    selecionados: List[int]


# ─── In-memory job store (backed by DB for persistence) ───────────────────────

_jobs_cache: dict = {}  # job_id -> dict (fast access; DB is source of truth)


def _update_job(job_id: str, status: str, resultado: dict = None,
                erro: str = None, progresso: dict = None):
    """Update job both in cache and DB."""
    from backend.db import atualizar_agent_job

    update = {"status": status}
    if resultado is not None:
        update["resultado"] = resultado
    if erro:
        update["erro"] = erro
    if progresso:
        update["progresso"] = progresso

    # Update cache
    if job_id in _jobs_cache:
        _jobs_cache[job_id].update(update)

    # Update DB
    try:
        atualizar_agent_job(
            job_id,
            status=status,
            resultado=json.dumps(resultado, ensure_ascii=False) if resultado else None,
            erro=erro,
            progresso=json.dumps(progresso, ensure_ascii=False) if progresso else None,
        )
    except Exception as e:
        log.error(f"Agent: Failed to persist job {job_id}: {e}")


# ─── Background Workers ──────────────────────────────────────────────────────

def _run_single_analysis(job_id: str, audit: dict, avaliacao: dict,
                         api_key: str, provider: str, base_url: str,
                         economico: bool):
    """Background worker for single subitem analysis."""
    from backend.agent.decision_engine import analyze_single_subitem

    _update_job(job_id, "running")
    try:
        result = analyze_single_subitem(
            audit=audit,
            avaliacao=avaliacao,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
            economico=economico,
        )
        if result.get("status") == "error":
            _update_job(job_id, "error", erro=result.get("erro", "Erro desconhecido"))
        else:
            _update_job(job_id, "done", resultado=result)
    except Exception as e:
        log.error(f"Agent job {job_id} failed: {traceback.format_exc()}")
        _update_job(job_id, "error", erro=str(e))


def _run_selection_analysis(job_id: str, audit: dict, avaliacoes: list,
                            selected_ids: list, api_key: str, provider: str,
                            base_url: str, economico: bool):
    """Background worker for custom selection analysis."""
    from backend.agent.decision_engine import analyze_selection

    _update_job(job_id, "running")
    try:
        def on_progress(current, total, av_id, result):
            _update_job(job_id, "running", progresso={
                "current": current,
                "total": total,
                "avaliacao_id": av_id,
                "ultima_decisao": result.get("decisao") if result else None,
            })

        result = analyze_selection(
            audit=audit,
            avaliacoes=avaliacoes,
            selected_ids=selected_ids,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
            economico=economico,
            on_progress=on_progress,
        )
        _update_job(job_id, "done", resultado=result)
    except Exception as e:
        log.error(f"Agent selection job {job_id} failed: {traceback.format_exc()}")
        _update_job(job_id, "error", erro=str(e))


def _run_batch_analysis(job_id: str, audit: dict, avaliacoes: list,
                        api_key: str, provider: str, base_url: str,
                        economico: bool):
    """Background worker for batch (all pending) analysis."""
    from backend.agent.decision_engine import analyze_all_pending

    _update_job(job_id, "running")
    try:
        def on_progress(current, total, av_id, result):
            _update_job(job_id, "running", progresso={
                "current": current,
                "total": total,
                "avaliacao_id": av_id,
                "ultima_decisao": result.get("decisao") if result else None,
            })

        result = analyze_all_pending(
            audit=audit,
            avaliacoes=avaliacoes,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
            economico=economico,
            on_progress=on_progress,
        )
        _update_job(job_id, "done", resultado=result)
    except Exception as e:
        log.error(f"Agent batch job {job_id} failed: {traceback.format_exc()}")
        _update_job(job_id, "error", erro=str(e))


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analisar/{auditoria_id}/{avaliacao_id}")
def analisar_subitem(auditoria_id: int, avaliacao_id: int,
                     body: AgentAnalyzeRequest = AgentAnalyzeRequest()):
    """
    Start an autonomous analysis of a single subitem.
    Uses evidence files already associated with the audit.
    Returns a job_id for polling.
    """
    from backend.db import get_auditoria, get_avaliacao, criar_agent_job

    # Validate audit
    audit = get_auditoria(auditoria_id)
    if not audit:
        raise HTTPException(404, "Auditoria não encontrada")

    # Validate avaliacao
    av = get_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(404, "Avaliação não encontrada")
    if av["auditoria_id"] != auditoria_id:
        raise HTTPException(400, "Avaliação não pertence a esta auditoria")

    # Create job
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()

    job_data = {
        "id": job_id,
        "auditoria_id": auditoria_id,
        "tipo": "single",
        "status": "pending",
        "data_criacao": now,
        "avaliacao_id": avaliacao_id,
        "pratica_num": av["pratica_num"],
        "subitem_idx": av["subitem_idx"],
    }
    _jobs_cache[job_id] = job_data

    try:
        criar_agent_job(
            job_id=job_id,
            auditoria_id=auditoria_id,
            tipo="single",
            pratica_num=av["pratica_num"],
            subitem_idx=av["subitem_idx"],
            nota_self_assessment=av.get("nota_self_assessment"),
        )
    except Exception as e:
        log.warning(f"Agent: Could not persist job to DB: {e}")

    # Submit to thread pool
    _executor.submit(
        _run_single_analysis, job_id, audit, av,
        body.api_key, body.provider, body.base_url, body.economico
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Análise do subitem {av['pratica_num']}.{av['subitem_idx']+1} iniciada",
    }


@router.post("/analisar-todos/{auditoria_id}")
def analisar_todos(auditoria_id: int,
                   body: AgentAnalyzeRequest = AgentAnalyzeRequest()):
    """
    Start autonomous analysis of ALL pending subitems for an audit.
    Returns a job_id for polling progress.
    """
    from backend.db import get_auditoria, carregar_avaliacoes, criar_agent_job

    audit = get_auditoria(auditoria_id)
    if not audit:
        raise HTTPException(404, "Auditoria não encontrada")

    avaliacoes = carregar_avaliacoes(auditoria_id)
    if not avaliacoes:
        raise HTTPException(400, "Nenhuma avaliação encontrada para esta auditoria")

    pending = [av for av in avaliacoes if (av.get("ia_status") or "") != "ok"]
    if not pending:
        return {
            "job_id": None,
            "status": "done",
            "message": "Todos os subitens já foram analisados pela IA",
            "total_subitens": len(avaliacoes),
            "pendentes": 0,
        }

    # Create batch job
    job_id = f"batch_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    job_data = {
        "id": job_id,
        "auditoria_id": auditoria_id,
        "tipo": "batch",
        "status": "pending",
        "data_criacao": now,
        "total_pendentes": len(pending),
    }
    _jobs_cache[job_id] = job_data

    try:
        criar_agent_job(
            job_id=job_id,
            auditoria_id=auditoria_id,
            tipo="batch",
        )
    except Exception as e:
        log.warning(f"Agent: Could not persist batch job to DB: {e}")

    # Submit to thread pool
    _executor.submit(
        _run_batch_analysis, job_id, audit, avaliacoes,
        body.api_key, body.provider, body.base_url, body.economico
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Análise em lote iniciada: {len(pending)} subitens pendentes",
        "total_subitens": len(avaliacoes),
        "pendentes": len(pending),
    }


@router.post("/analisar-selecao/{auditoria_id}")
def analisar_selecao(auditoria_id: int, body: AgentSelectionRequest):
    """
    Starts an autonomous analysis of a SPECIFIC LIST of subitems.
    """
    from backend.db import get_auditoria, carregar_avaliacoes, criar_agent_job

    audit = get_auditoria(auditoria_id)
    if not audit:
        raise HTTPException(404, "Auditoria não encontrada")

    if not body.selecionados:
        raise HTTPException(400, "Nenhum subitem selecionado")

    avaliacoes = carregar_avaliacoes(auditoria_id)
    avaliacoes_map = {av["id"]: av for av in avaliacoes}
    
    confirmados = [av_id for av_id in body.selecionados if av_id in avaliacoes_map]
    
    if not confirmados:
        raise HTTPException(400, "Nenhum dos subitens selecionados foi encontrado nesta auditoria")

    # Create selection job
    job_id = f"sel_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    job_data = {
        "id": job_id,
        "auditoria_id": auditoria_id,
        "tipo": "batch",
        "status": "pending",
        "data_criacao": now,
        "total_pendentes": len(confirmados),
    }
    _jobs_cache[job_id] = job_data

    try:
        criar_agent_job(
            job_id=job_id,
            auditoria_id=auditoria_id,
            tipo="batch",
        )
    except Exception as e:
        log.warning(f"Agent: Could not persist selection job to DB: {e}")

    # Submit to thread pool
    _executor.submit(
        _run_selection_analysis, job_id, audit, avaliacoes, confirmados,
        body.api_key, body.provider, body.base_url, body.economico
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Análise de seleção iniciada: {len(confirmados)} subitens",
    }


@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    """Get the current status of an analysis job."""
    from backend.db import get_agent_job

    # Try cache first
    if job_id in _jobs_cache:
        job = _jobs_cache[job_id]
        return {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "tipo": job.get("tipo"),
            "auditoria_id": job.get("auditoria_id"),
            "progresso": job.get("progresso"),
            "erro": job.get("erro"),
        }

    # Fallback to DB
    job = get_agent_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "tipo": job.get("tipo"),
        "auditoria_id": job.get("auditoria_id"),
        "progresso": json.loads(job["progresso"]) if job.get("progresso") else None,
        "erro": job.get("erro"),
    }


@router.get("/resultado/{job_id}")
def get_job_result(job_id: str):
    """Get the full result of a completed analysis job."""
    from backend.db import get_agent_job

    # Try cache first
    if job_id in _jobs_cache:
        job = _jobs_cache[job_id]
        if job.get("status") != "done":
            return {
                "job_id": job_id,
                "status": job.get("status"),
                "message": "Análise ainda em andamento" if job.get("status") == "running" else "Aguardando início",
                "progresso": job.get("progresso"),
                "erro": job.get("erro"),
            }
        return {
            "job_id": job_id,
            "status": "done",
            "resultado": job.get("resultado"),
        }

    # Fallback to DB
    job = get_agent_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado")

    if job.get("status") != "done":
        return {
            "job_id": job_id,
            "status": job.get("status"),
            "erro": job.get("erro"),
        }

    resultado = job.get("resultado")
    if resultado and isinstance(resultado, str):
        try:
            resultado = json.loads(resultado)
        except Exception:
            pass

    return {
        "job_id": job_id,
        "status": "done",
        "resultado": resultado,
    }


@router.get("/jobs/{auditoria_id}")
def list_audit_jobs(auditoria_id: int):
    """List all agent jobs for a specific audit."""
    from backend.db import listar_agent_jobs

    jobs = listar_agent_jobs(auditoria_id)
    return {"auditoria_id": auditoria_id, "jobs": jobs}
