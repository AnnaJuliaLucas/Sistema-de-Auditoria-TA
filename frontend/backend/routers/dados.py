"""
routers/dados.py — Endpoints for data management & history.
Database-agnostic: works with both SQLite and PostgreSQL.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.db import (
    listar_auditorias, get_auditoria, atualizar_status,
    excluir_auditoria, duplicar_auditoria,
    comparativo_ciclos, carregar_audit_log,
)

router = APIRouter(prefix="/api/dados", tags=["dados"])


class DuplicarBody(BaseModel):
    novo_ciclo: str


# ── Histórico de Ciclos (reutiliza listar_auditorias) ──────────────────────

@router.get("/auditorias")
def list_all_auditorias():
    """List all audits with statistics (same as /api/auditorias but grouped here for the Dados page)."""
    return listar_auditorias()


# ── Excluir Auditoria ─────────────────────────────────────────────────────

@router.delete("/auditorias/{auditoria_id}")
def delete_auditoria(auditoria_id: int):
    """Delete an audit and all associated data. Creates a backup before deleting (SQLite only)."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    excluir_auditoria(auditoria_id)
    return {"ok": True, "message": f"Auditoria {auditoria_id} excluída com sucesso"}


# ── Duplicar Auditoria ────────────────────────────────────────────────────

@router.post("/auditorias/{auditoria_id}/duplicar")
def duplicate_auditoria(auditoria_id: int, body: DuplicarBody):
    """Duplicate an audit to a new cycle. Copies structure without decisions/AI analysis."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    if not body.novo_ciclo.strip():
        raise HTTPException(status_code=400, detail="Ciclo não pode ser vazio")
    novo_id = duplicar_auditoria(auditoria_id, body.novo_ciclo.strip())
    if not novo_id:
        raise HTTPException(status_code=500, detail="Falha ao duplicar auditoria")
    return {"ok": True, "novo_id": novo_id, "novo_ciclo": body.novo_ciclo.strip()}


# ── Comparativo entre Ciclos ──────────────────────────────────────────────

@router.get("/comparativo")
def get_comparativo(id_a: int = Query(...), id_b: int = Query(...)):
    """Compare scores between two audit cycles."""
    aud_a = get_auditoria(id_a)
    aud_b = get_auditoria(id_b)
    if not aud_a or not aud_b:
        raise HTTPException(status_code=404, detail="Uma ou ambas auditorias não encontradas")
    resultado = comparativo_ciclos(id_a, id_b)
    return {
        "auditoria_a": {"id": id_a, "unidade": aud_a["unidade"], "area": aud_a["area"], "ciclo": aud_a["ciclo"]},
        "auditoria_b": {"id": id_b, "unidade": aud_b["unidade"], "area": aud_b["area"], "ciclo": aud_b["ciclo"]},
        "comparativo": resultado,
    }


# ── Audit Log ─────────────────────────────────────────────────────────────

@router.get("/audit-log")
def get_audit_log(auditoria_id: int = Query(None), limit: int = Query(200)):
    """Get audit change log entries."""
    return carregar_audit_log(auditoria_id=auditoria_id, limit=limit)
