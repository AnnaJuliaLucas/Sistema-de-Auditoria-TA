"""
routers/export.py — Excel export and new audit creation.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.db import get_db, get_auditoria, carregar_avaliacoes, _safe_int
from datetime import datetime
from pathlib import Path
import tempfile
import json
import sys

_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api", tags=["export"])


class NovaAuditoria(BaseModel):
    unidade: str
    area: str
    ciclo: str
    assessment_file_path: str = ""
    evidence_folder_path: str = ""
    openai_api_key: str = ""
    observacoes: str = ""
    modo_analise: str = "completo"


@router.post("/auditorias")
def criar_auditoria(body: NovaAuditoria):
    """Create a new audit."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO auditorias
                    (unidade, area, ciclo, data_criacao, data_atualizacao,
                     status, assessment_file_path, evidence_folder_path,
                     openai_api_key, observacoes, modo_analise)
                VALUES (?,?,?,?,?,'em_andamento',?,?,?,?,?)
            """, (body.unidade, body.area, body.ciclo, now, now,
                  body.assessment_file_path, body.evidence_folder_path,
                  body.openai_api_key, body.observacoes, body.modo_analise))
            row = conn.execute(
                "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
                (body.unidade, body.area, body.ciclo)
            ).fetchone()
            audit_id = row["id"] if row else None
        except Exception:
            row = conn.execute(
                "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
                (body.unidade, body.area, body.ciclo)
            ).fetchone()
            audit_id = row["id"] if row else None

    if not audit_id:
        raise HTTPException(status_code=500, detail="Falha ao criar auditoria")

    # Parse assessment file if provided
    if body.assessment_file_path and Path(body.assessment_file_path).exists():
        try:
            from checklist_po_aut_002 import CHECKLIST
            # Import subitems from checklist
            with get_db() as conn:
                for pratica in CHECKLIST:
                    for sub in pratica.get("subitens", []):
                        conn.execute("""
                            INSERT OR IGNORE INTO avaliacoes
                                (auditoria_id, pratica_num, pratica_nome,
                                 subitem_idx, subitem_nome, evidencia_descricao,
                                 nivel_0, nivel_1, nivel_2, nivel_3, nivel_4,
                                 nota_self_assessment, decisao)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pendente')
                        """, (
                            audit_id, pratica["num"], pratica["nome"],
                            sub["idx"], sub["nome"], sub.get("evidencia", ""),
                            sub.get("nivel_0", ""), sub.get("nivel_1", ""),
                            sub.get("nivel_2", ""), sub.get("nivel_3", ""),
                            sub.get("nivel_4", ""), sub.get("nota_sa")
                        ))
        except Exception:
            pass

    return {"ok": True, "id": audit_id}


@router.post("/auditorias/{auditoria_id}/importar-assessment")
def importar_assessment(auditoria_id: int, assessment_path: str = ""):
    """Parse and import assessment Excel file for an audit."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    path = assessment_path or aud.get("assessment_file_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=400, detail="Arquivo de assessment não encontrado")

    try:
        # Use the existing parse_assessment function approach
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active

        imported = 0
        with get_db() as conn:
            current_pratica_num = None
            current_pratica_nome = ""
            sub_idx = 0

            for row in ws.iter_rows(min_row=2, values_only=False):
                vals = [cell.value for cell in row]
                if not any(vals):
                    continue

                # Detect practice row vs subitem row based on structure
                if vals[0] and str(vals[0]).strip().isdigit():
                    current_pratica_num = int(vals[0])
                    current_pratica_nome = str(vals[1] or "").strip()
                    sub_idx = 0
                elif current_pratica_num and vals[1]:
                    nota_sa = _safe_int(vals[-1]) if vals[-1] else None
                    conn.execute("""
                        INSERT OR IGNORE INTO avaliacoes
                            (auditoria_id, pratica_num, pratica_nome,
                             subitem_idx, subitem_nome, nota_self_assessment, decisao)
                        VALUES (?,?,?,?,?,?,'pendente')
                    """, (
                        auditoria_id, current_pratica_num, current_pratica_nome,
                        sub_idx, str(vals[1]).strip(), nota_sa
                    ))
                    sub_idx += 1
                    imported += 1

        return {"ok": True, "imported": imported}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao importar: {str(e)}")


@router.get("/auditorias/{auditoria_id}/exportar-excel")
def exportar_excel(auditoria_id: int):
    """Export audit data as Excel file matching legacy formatting."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    df_aval = carregar_avaliacoes(auditoria_id)
    if not df_aval:
        raise HTTPException(status_code=400, detail="Nenhuma avaliação para exportar")

    try:
        import openpyxl
        import io
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Análise de Auditoria"

        # Cores para um visual mais profissional e de auditoria
        COR_TITULO_PRINCIPAL_FUNDO = "002060"  # Azul Escuro
        COR_TITULO_PRINCIPAL_FONTE = "FFFFFF"  # Branco
        COR_CABECALHO_FUNDO = "D9D9D9"       # Cinza Claro
        COR_CABECALHO_FONTE = "000000"       # Preto
        COR_PRATICA_FUNDO = "DDEBF7"         # Azul Médio Claro
        COR_PRATICA_FONTE = "002060"         # Azul Escuro
        COR_PADRAO_FONTE = "000000"          # Preto

        # Cores para formatação condicional
        COR_DIMINUI_FUNDO = "FF0000"         # Vermelho
        COR_AUMENTA_FUNDO = "00B0F0"         # Azul Claro
        COR_PERMANECE_FUNDO = "00B050"       # Verde Escuro
        COR_NAO_SE_APLICA_FUNDO = "FFC000"   # Laranja
        COR_EVID_INSUF_FUNDO = "FFFF00"      # Amarelo
        COR_EVID_INEXIST_FUNDO = "A6A6A6"    # Cinza Médio
        COR_FONTE_BRANCA = "FFFFFF"          # Branco

        def fill(h): return PatternFill(start_color=h, end_color=h, fill_type="solid")
        thin_side = Side(style='thin', color="000000")
        medium_side = Side(style='medium', color="000000")
        brd_thin = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        brd_medium_left = Border(left=medium_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 1. Título Principal (Linha 1)
        ws.merge_cells("A1:F1")
        ws["A1"].value = f"FORMULÁRIO PARA ANÁLISE DAS NOTAS DO SELF ASSESSMENT DA {aud['area'].upper()} DE {aud['unidade'].upper()}"
        ws["A1"].fill = fill(COR_TITULO_PRINCIPAL_FUNDO)
        ws["A1"].font = Font(name='Arial', size=14, bold=True, color=COR_TITULO_PRINCIPAL_FONTE)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 40

        # 2. Cabeçalhos (Linha 2)
        headers = ["PRÁTICAS", "Nota", "Status da Nota", "Tipo de Não Conformidade", "Descrição da Não Conformidade", "Comentários Adicionais"]
        widths = [67, 17, 18, 28, 93, 107]
        for ci, (h, w) in enumerate(zip(headers, widths), 1):
            c = ws.cell(row=2, column=ci, value=h)
            c.fill = fill(COR_CABECALHO_FUNDO)
            c.font = Font(name='Arial', size=10, bold=True, color=COR_CABECALHO_FONTE)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = brd_thin
            ws.column_dimensions[get_column_letter(ci)].width = w
        ws.row_dimensions[2].height = 25

        # 3. Conteúdo
        pratica_atual = None
        row = 3
        status_map = {"permanece": "Permanece", "insuficiente": "Diminui", "inexistente": "Diminui", "aumenta": "Aumenta", "pendente": ""}
        tipo_map = {'permanece': 'Não se aplica', 'insuficiente': 'Evidências insuficiente', 'inexistente': 'Evidências inexistente', 'pendente': ''}

        import pandas as pd
        if not isinstance(df_aval, pd.DataFrame):
            df_aval = pd.DataFrame(df_aval)

        for _, av in df_aval.iterrows():
            # Linha de Prática (Título da Seção)
            if av['pratica_num'] != pratica_atual:
                pratica_atual = av['pratica_num']
                ws.merge_cells(f"A{row}:F{row}")
                c = ws[f"A{row}"]
                c.value = f"{av['pratica_num']} - {av['pratica_nome'].upper()}"
                c.fill = fill(COR_PRATICA_FUNDO)
                c.font = Font(name='Arial', size=10, bold=True, color=COR_PRATICA_FONTE)
                c.alignment = Alignment(vertical="center")
                c.border = brd_thin
                ws.row_dimensions[row].height = 20
                row += 1

            # Linha de Subitem
            d = av['decisao'] or 'pendente'
            
            vals = [
                av['subitem_nome'],
                av['nota_self_assessment'] if pd.notna(av['nota_self_assessment']) else '',
                status_map.get(d, ''),
                tipo_map.get(d, ''),
                av.get('descricao_nc', '') or '',
                av.get('comentarios', '') or ''
            ]

            for ci, val in enumerate(vals, 1):
                c = ws.cell(row=row, column=ci, value=val)
                c.font = Font(name='Arial', size=10, color=COR_PADRAO_FONTE)
                c.alignment = Alignment(wrap_text=True, vertical="center")
                c.border = brd_medium_left if ci == 1 else brd_thin

                # Formatação condicional para Status da Nota (Coluna C, ci=3)
                if ci == 3:
                    if val == "Diminui":
                        c.fill = fill(COR_DIMINUI_FUNDO)
                        c.font = Font(name='Arial', size=10, bold=True, color=COR_FONTE_BRANCA)
                    elif val == "Aumenta":
                        c.fill = fill(COR_AUMENTA_FUNDO)
                        c.font = Font(name='Arial', size=10, bold=True, color=COR_FONTE_BRANCA)
                    elif val == "Permanece":
                        c.fill = fill(COR_PERMANECE_FUNDO)
                        c.font = Font(name='Arial', size=10, bold=True, color=COR_FONTE_BRANCA)
                    c.alignment = Alignment(horizontal="center", vertical="center")

                # Formatação condicional para Tipo de Não Conformidade (Coluna D, ci=4)
                elif ci == 4:
                    if val == "Não se aplica":
                        c.fill = fill(COR_NAO_SE_APLICA_FUNDO)
                    elif val == "Evidências insuficiente":
                        c.fill = fill(COR_EVID_INSUF_FUNDO)
                    elif val == "Evidências inexistente":
                        c.fill = fill(COR_EVID_INEXIST_FUNDO)
                    c.alignment = Alignment(horizontal="center", vertical="center")
                
                # Centralizar Nota (Coluna B, ci=2)
                elif ci == 2:
                    c.alignment = Alignment(horizontal="center", vertical="center")
            
            # Ajustar altura da linha
            desc_len = len(str(vals[4])) if vals[4] else 0
            coment_len = len(str(vals[5])) if vals[5] else 0
            max_len = max(desc_len, coment_len)
            num_linhas = max(1, max_len / 80)
            ws.row_dimensions[row].height = max(30, num_linhas * 15)
            row += 1

        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(tmp.name)
        tmp.close()

        filename = f"Analise_{aud['area'].replace(' ','_')}_{aud['unidade'].replace(' ','_')}_{aud.get('ciclo','')}.xlsx"
        return FileResponse(tmp.name, filename=filename,
                          media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação: {str(e)}")


@router.get("/unidades-areas")
def get_unidades_areas():
    """Return available units and areas for new audit creation."""
    return {
        "Juiz de Fora": ["Utilidades", "Aciaria", "Laminação", "Redução"],
        "Piracicaba": ["Aciaria", "Utilidades", "Laminação"],
        "Sitrel": ["Laminação"],
        "Mina do Andrade": ["Mineração"],
        "João Monlevade": ["Aciaria", "Laminação TL2", "Laminação TL3", "Utilidades", "Alto Forno", "Sinterização", "GACAT"],
        "Trefilarias": ["São Paulo", "Sabará", "Resende", "Juiz de Fora"],
        "Sul Fluminense": ["Aciaria (RS)", "Utilidades (RS)", "Laminação (RS)", "Laminação (BM)", "Utilidades (BM)"],
    }
