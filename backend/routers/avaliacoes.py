"""
routers/avaliacoes.py — Endpoints for evaluation/decision operations.
"""
from fastapi import APIRouter, HTTPException
from backend.db import carregar_avaliacoes, get_avaliacao, salvar_decisao
from backend.models import DecisaoUpdate, NotaPreview
from backend.auth import get_current_user
from fastapi import Depends

router = APIRouter(prefix="/api", tags=["avaliacoes"])


def calcular_nota_final(nota_sa: int, decisao: str, nota_livre: int = None) -> int | None:
    """Calculate final grade based on decision type."""
    if nota_sa is None:
        return None
    if decisao == "permanece":
        return nota_sa
    if decisao == "insuficiente":
        if nota_livre is not None:
            return max(0, min(int(nota_livre), max(0, nota_sa - 1)))
        return max(0, nota_sa - 1)
    if decisao == "inexistente":
        return 0
    if decisao == "aumentar":
        if nota_livre is not None:
            return min(4, max(nota_sa + 1, int(nota_livre)))
        return min(4, nota_sa + 1)
    return None  # pendente


@router.get("/auditorias/{auditoria_id}/avaliacoes")
def list_avaliacoes(auditoria_id: int, current_user: str = Depends(get_current_user)):
    """List all evaluations for an audit, grouped by practice."""
    avaliacoes = carregar_avaliacoes(auditoria_id)

    # Group by practice
    praticas = {}
    for av in avaliacoes:
        pnum = av.get("pratica_num")
        if pnum not in praticas:
            praticas[pnum] = {
                "pratica_num": pnum,
                "pratica_nome": av.get("pratica_nome", ""),
                "subitens": [],
                "media_sa": 0,
                "media_final": None,
                "total": 0,
                "avaliados": 0,
                "ia_ok": 0,
                "pendentes": 0,
            }
        praticas[pnum]["subitens"].append(av)
        praticas[pnum]["total"] += 1
        if av.get("decisao") and av["decisao"] != "pendente":
            praticas[pnum]["avaliados"] += 1
        else:
            praticas[pnum]["pendentes"] += 1
        if av.get("ia_status") == "ok":
            praticas[pnum]["ia_ok"] += 1

    # Calculate averages
    for p in praticas.values():
        sas = [s["nota_self_assessment"] for s in p["subitens"] if s.get("nota_self_assessment") is not None]
        finals = [s["nota_final"] for s in p["subitens"] if s.get("nota_final") is not None]
        p["media_sa"] = round(sum(sas) / len(sas), 1) if sas else 0
        p["media_final"] = round(sum(finals) / len(finals), 1) if finals else None

    result = sorted(praticas.values(), key=lambda x: x["pratica_num"] or 0)
    return result


@router.put("/avaliacoes/{avaliacao_id}/decisao")
def update_decisao(avaliacao_id: int, body: DecisaoUpdate, current_user: str = Depends(get_current_user)):
    """Save auditor's manual decision for a subitem."""
    av = get_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")

    # Calculate nota_final based on decision if not explicitly provided
    nota_sa = av.get("nota_self_assessment")
    if body.decisao == "pendente":
        nota_final = None
    elif body.nota_final is not None:
        nota_final = body.nota_final
    else:
        nota_final = calcular_nota_final(nota_sa, body.decisao)

    salvar_decisao(
        avaliacao_id, body.decisao, nota_final,
        body.descricao_nc, body.comentarios, usuario=current_user
    )

    return {
        "ok": True,
        "decisao": body.decisao,
        "nota_final": nota_final,
    }


@router.post("/avaliacoes/nota-preview")
def preview_nota(body: NotaPreview, current_user: str = Depends(get_current_user)):
    """Preview what the final grade would be for a given decision."""
    nota = calcular_nota_final(body.nota_sa, body.decisao, body.nota_livre)
    return {"nota_final": nota}


@router.get("/avaliacoes/{avaliacao_id}")
def get_avaliacao_detail(avaliacao_id: int, current_user: str = Depends(get_current_user)):
    """Get single evaluation details."""
    av = get_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    return av
