"""
routers/auditorias.py — Endpoints for audit CRUD operations.
"""
from fastapi import APIRouter, HTTPException
from backend.db import listar_auditorias, get_auditoria, atualizar_status, atualizar_config, estatisticas_auditoria
from backend.models import AuditoriaOut, StatusUpdate, AuditoriaConfig, EstatisticasOut
from backend.auth import get_current_user
from fastapi import Depends

router = APIRouter(prefix="/api/auditorias", tags=["auditorias"])


@router.get("")
def list_auditorias(current_user: str = Depends(get_current_user)):
    """List all audits with summary statistics."""
    auditorias = listar_auditorias()
    return auditorias


@router.get("/{auditoria_id}")
def get_auditoria_detail(auditoria_id: int, current_user: str = Depends(get_current_user)):
    """Get single audit details."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return aud


@router.put("/{auditoria_id}/status")
def update_status(auditoria_id: int, body: StatusUpdate, current_user: str = Depends(get_current_user)):
    """Update audit status."""
    valid = {"em_andamento", "concluida", "em_revisao", "aprovada", "arquivada"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {valid}")
    atualizar_status(auditoria_id, body.status, usuario=current_user)
    return {"ok": True, "status": body.status}


@router.put("/{auditoria_id}/config")
def update_config(auditoria_id: int, body: AuditoriaConfig, current_user: str = Depends(get_current_user)):
    """Update audit configuration (paths, API key)."""
    atualizar_config(
        auditoria_id, body.assessment_file_path,
        body.evidence_folder_path, body.openai_api_key,
        body.observacoes, body.modo_analise
    )
    return {"ok": True}


@router.get("/{auditoria_id}/estatisticas")
def get_estatisticas(auditoria_id: int, current_user: str = Depends(get_current_user)):
    """Get audit summary statistics."""
    stats = estatisticas_auditoria(auditoria_id)
    return stats
