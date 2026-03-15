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
    """Update audit status and cleanup files if concluded."""
    valid = {"em_andamento", "concluida", "em_revisao", "aprovada", "arquivada"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {valid}")
    
    atualizar_status(auditoria_id, body.status, usuario=current_user)
    
    # Se mudar de "em_andamento" para qualquer outro, apagamos a pasta local para economizar espaço
    if body.status != "em_andamento":
        import shutil
        from backend.db import BASE_DIR
        audit_dir = BASE_DIR / "uploads" / str(auditoria_id)
        if audit_dir.exists():
            shutil.rmtree(audit_dir)
            import logging
            logging.getLogger("auditoria_auditorias").info(f"Storage cleanup: Deleted folder {audit_dir} for audit {auditoria_id} (status: {body.status})")
            
    return {"ok": True, "status": body.status}


@router.delete("/{auditoria_id}")
def delete_auditoria_endpoint(auditoria_id: int, current_user: str = Depends(get_current_user)):
    """Permanently delete an audit (DB + Disk)."""
    from backend.db import get_auditoria, deletar_auditoria, BASE_DIR
    import shutil
    import logging
    log = logging.getLogger("auditoria_auditorias")
    
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
        
    # 1. DB Cleanup
    deletar_auditoria(auditoria_id)
    
    # 2. Disk Cleanup
    audit_dir = BASE_DIR / "uploads" / str(auditoria_id)
    if audit_dir.exists():
        shutil.rmtree(audit_dir)
        log.info(f"Storage cleanup: Deleted folder {audit_dir} after audit {auditoria_id} deletion.")
        
    return {"ok": True, "message": f"Auditoria {auditoria_id} removida com sucesso."}


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
