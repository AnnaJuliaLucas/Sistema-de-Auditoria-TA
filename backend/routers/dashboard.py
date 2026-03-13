"""
routers/dashboard.py — Dashboard statistics and charts data.
"""
from fastapi import APIRouter
from backend.db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumo-geral")
def resumo_geral(auditoria_id: int = None):
    """Overall summary across all audits, or filtered by one."""
    with get_db() as conn:
        query = """
            SELECT
                COUNT(DISTINCT a.id) AS total_auditorias,
                COUNT(av.id) AS total_subitens,
                SUM(CASE WHEN av.decisao != 'pendente' AND av.decisao IS NOT NULL THEN 1 ELSE 0 END) AS avaliados,
                SUM(CASE WHEN av.ia_status = 'ok' THEN 1 ELSE 0 END) AS ia_analisados,
                AVG(CASE WHEN av.nota_final IS NOT NULL THEN CAST(av.nota_final AS REAL) END) AS media_geral
            FROM auditorias a
            LEFT JOIN avaliacoes av ON av.auditoria_id = a.id
        """
        if auditoria_id:
            query += " WHERE a.id = ?"
            row = conn.execute(query, (auditoria_id,)).fetchone()
        else:
            row = conn.execute(query).fetchone()
        
        return dict(row) if row else {}


@router.get("/distribuicao-notas/{auditoria_id}")
def distribuicao_notas(auditoria_id: int):
    """Distribution of final grades for an audit."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT nota_final, COUNT(*) as count
            FROM avaliacoes
            WHERE auditoria_id=? AND nota_final IS NOT NULL
            GROUP BY nota_final
            ORDER BY nota_final
        """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]


@router.get("/distribuicao-decisoes/{auditoria_id}")
def distribuicao_decisoes(auditoria_id: int):
    """Distribution of decisions for an audit."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                COALESCE(decisao, 'pendente') as decisao,
                COUNT(*) as count
            FROM avaliacoes
            WHERE auditoria_id=?
            GROUP BY decisao
            ORDER BY count DESC
        """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]


@router.get("/media-por-pratica/{auditoria_id}")
def media_por_pratica(auditoria_id: int):
    """Average SA and Final grades per practice."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                pratica_num,
                pratica_nome,
                AVG(CAST(nota_self_assessment AS REAL)) AS media_sa,
                AVG(CASE WHEN nota_final IS NOT NULL THEN CAST(nota_final AS REAL) END) AS media_final,
                COUNT(*) AS total,
                SUM(CASE WHEN decisao != 'pendente' AND decisao IS NOT NULL THEN 1 ELSE 0 END) AS avaliados
            FROM avaliacoes
            WHERE auditoria_id=?
            GROUP BY pratica_num
            ORDER BY pratica_num
        """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]


@router.get("/atividade-recente")
def atividade_recente():
    """Recent audit log activity."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT al.*, a.unidade, a.area, a.ciclo
            FROM audit_log al
            LEFT JOIN auditorias a ON a.id = al.auditoria_id
            ORDER BY al.timestamp DESC
            LIMIT 20
        """).fetchall()
        return [dict(r) for r in rows]
