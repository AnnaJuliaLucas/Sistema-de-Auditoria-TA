"""
routers/chat.py — AI collaborative chat endpoints.
"""
from fastapi import APIRouter, HTTPException
from backend.db import get_auditoria, get_avaliacao, carregar_chat, salvar_mensagem_chat, salvar_decisao
from backend.models import IAChatRequest
import sys
from pathlib import Path

_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/{auditoria_id}/{pratica_num}/{subitem_idx}")
def get_chat_history(auditoria_id: int, pratica_num: int, subitem_idx: int):
    """Get chat history for a subitem."""
    msgs = carregar_chat(auditoria_id, pratica_num, subitem_idx)
    return msgs


@router.post("/{avaliacao_id}")
def send_chat_message(avaliacao_id: int, body: IAChatRequest):
    """Send message to AI and get response with optional decision revision."""
    av = get_avaliacao(avaliacao_id)
    if not av:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")

    aud = get_auditoria(av["auditoria_id"])
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    api_key = body.api_key or aud.get("openai_api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave API não configurada")

    auditoria_id = av["auditoria_id"]
    pratica_num = av["pratica_num"]
    subitem_idx = av["subitem_idx"]

    # Save user message
    salvar_mensagem_chat(
        auditoria_id, pratica_num, subitem_idx,
        "user", body.message
    )

    # Get chat history
    history = carregar_chat(auditoria_id, pratica_num, subitem_idx)

    try:
        from ai_analyzer import AuditAIAnalyzer

        analyzer = AuditAIAnalyzer(api_key=api_key, economico=body.economico)

        # Build context
        context = f"""Contexto do subitem:
- Prática: {av['pratica_nome']}
- Subitem: {av['subitem_nome']}
- Nota Self-Assessment: {av.get('nota_self_assessment', 'N/A')}
- Decisão atual: {av.get('decisao', 'pendente')}
- Nota final atual: {av.get('nota_final', 'N/A')}
- Análise IA anterior: {(av.get('ia_analise_detalhada') or 'Nenhuma')[:500]}"""

        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": f"""Você é um especialista em auditoria de automação industrial (PO.AUT.002).
Ajude o auditor a revisar a avaliação deste subitem. Seja conciso e objetivo.
Se o auditor discordar da IA, aceite e sugira ajustes na decisão/nota.

{context}"""}
        ]

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("conteudo", msg.get("content", ""))
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        # Call OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini" if body.economico else "gpt-4o",
            messages=messages,
            max_tokens=800,
            temperature=0.3,
        )

        ai_response = response.choices[0].message.content or ""

        # Save AI response
        salvar_mensagem_chat(
            auditoria_id, pratica_num, subitem_idx,
            "assistant", ai_response,
            decisao_snapshot=av.get("decisao"),
            nota_snapshot=av.get("nota_final"),
        )

        return {
            "ok": True,
            "response": ai_response,
            "role": "assistant",
        }

    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        salvar_mensagem_chat(
            auditoria_id, pratica_num, subitem_idx,
            "sistema", error_msg
        )
        raise HTTPException(status_code=500, detail=str(e))
