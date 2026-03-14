from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db import get_db, get_system_config, set_system_config, listar_conhecimento, get_auditoria, delete_vercel_blobs
import os
import subprocess
from pathlib import Path

router = APIRouter(prefix="/api/config", tags=["config"])

class GlobalConfig(BaseModel):
    openai_api_key: str = ""
    ai_provider: str = "openai"
    ai_base_url: str = ""
    default_modo_analise: str = "completo"

@router.get("/global")
def get_global_config():
    """Retrieve global system settings."""
    # Mask API key for security in GET
    raw_key = get_system_config("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
    masked_key = ""
    if raw_key:
        if len(raw_key) > 8:
            masked_key = raw_key[:4] + "*" * (len(raw_key) - 8) + raw_key[-4:]
        else:
            masked_key = "****"
            
    return {
        "openai_api_key": masked_key,
        "ai_provider": get_system_config("ai_provider", "openai"),
        "ai_base_url": get_system_config("ai_base_url", ""),
        "default_modo_analise": get_system_config("default_modo_analise", "completo"),
        "has_key": bool(raw_key),
        "db_path": os.environ.get("DATABASE_URL", "SQLite Local")
    }

@router.put("/global")
def update_global_config(body: GlobalConfig):
    """Update global system settings."""
    if body.openai_api_key and not body.openai_api_key.startswith("****"):
        # Only update if it's not the masked version or empty
        set_system_config("openai_api_key", body.openai_api_key)
        
    set_system_config("ai_provider", body.ai_provider)
    set_system_config("ai_base_url", body.ai_base_url)
    set_system_config("default_modo_analise", body.default_modo_analise)
    return {"ok": True}

@router.delete("/auditorias/{auditoria_id}")
def delete_auditoria(auditoria_id: int):
    """Delete an audit, all its evaluations, and associated Vercel Blobs."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
        
    # Collect blob URLs to delete
    blobs_to_delete = []
    if aud.get("assessment_file_path") and aud["assessment_file_path"].startswith("http"):
        blobs_to_delete.append(aud["assessment_file_path"])
    if aud.get("evidence_zip_url") and aud["evidence_zip_url"].startswith("http"):
        blobs_to_delete.append(aud["evidence_zip_url"])
        
    # Delete from Vercel Storage
    if blobs_to_delete:
        try:
            delete_vercel_blobs(blobs_to_delete)
        except Exception as e:
            print(f"Failed to delete blobs for audit {auditoria_id}: {e}")

    with get_db() as conn:
        conn.execute("DELETE FROM auditorias WHERE id = %s", (auditoria_id,))
    return {"ok": True}

# ── NOVO: Base de Conhecimento & Local AI ──

@router.get("/knowledge")
def get_knowledge_base(tag: str = None):
    """Retorna snippets da base de conhecimento."""
    return listar_conhecimento(tag)

@router.post("/knowledge/reindex")
def reindex_knowledge():
    """Aciona o script de re-indexação da base local."""
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "auditoria-ollama-gen.py"
    try:
        # Apenas indexar, sem recriar o modelo (pode demorar)
        # Podemos passar um argumento pro script se necessário, ou rodar o main que faz ambos.
        # Por enquanto vamos rodar o main pois o usuário quer o "Cérebro" pronto.
        subprocess.Popen([os.sys.executable, str(script_path)], shell=False)
        return {"ok": True, "message": "Indexação iniciada em segundo plano."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/local-ai/generate")
def generate_local_model():
    """Aciona a geração do modelo customizado no Ollama."""
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "auditoria-ollama-gen.py"
    try:
        subprocess.Popen([os.sys.executable, str(script_path)], shell=False)
        return {"ok": True, "message": "Geração do modelo local iniciada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
