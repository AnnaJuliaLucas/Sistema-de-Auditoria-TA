"""
routers/diario.py — Audit diary/notes endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.db import get_db
from datetime import datetime

router = APIRouter(prefix="/api/diario", tags=["diario"])


class DiarioEntry(BaseModel):
    conteudo: str
    tipo: str = "observacao"
    titulo: str = ""
    pratica_ref: str = ""
    prioridade: str = "normal"
    data_entrada: Optional[str] = None


@router.get("/{auditoria_id}")
def list_entries(auditoria_id: int, tipo: Optional[str] = None):
    """List diary entries for an audit."""
    with get_db() as conn:
        if tipo:
            rows = conn.execute("""
                SELECT * FROM diario_auditoria
                WHERE auditoria_id=? AND tipo=?
                ORDER BY data_entrada DESC, data_criacao DESC
            """, (auditoria_id, tipo)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM diario_auditoria
                WHERE auditoria_id=?
                ORDER BY data_entrada DESC, data_criacao DESC
            """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]


@router.post("/{auditoria_id}")
def create_entry(auditoria_id: int, body: DiarioEntry):
    """Create a new diary entry."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO diario_auditoria
                (auditoria_id, data_entrada, tipo, titulo, conteudo, pratica_ref, prioridade, data_criacao, data_atualizacao)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            auditoria_id,
            body.data_entrada or now[:10],
            body.tipo, body.titulo, body.conteudo,
            body.pratica_ref, body.prioridade, now, now
        ))
        return {"ok": True, "id": cursor.lastrowid}


@router.put("/{entry_id}/resolver")
def toggle_resolved(entry_id: int):
    """Toggle resolved status."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT resolvido FROM diario_auditoria WHERE id=?", (entry_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entrada não encontrada")
        new_val = 0 if row["resolvido"] else 1
        conn.execute(
            "UPDATE diario_auditoria SET resolvido=?, data_atualizacao=? WHERE id=?",
            (new_val, now, entry_id)
        )
        return {"ok": True, "resolvido": bool(new_val)}


@router.delete("/{entry_id}")
def delete_entry(entry_id: int):
    """Delete a diary entry."""
    with get_db() as conn:
        conn.execute("DELETE FROM diario_auditoria WHERE id=?", (entry_id,))
        return {"ok": True}
