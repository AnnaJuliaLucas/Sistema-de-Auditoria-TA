"""
routers/export.py — Excel export and new audit creation.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.db import get_db, get_auditoria, carregar_avaliacoes, _safe_int, USE_POSTGRES
from datetime import datetime
from pathlib import Path
import tempfile
import json
import sys
import os
import shutil
import zipfile

_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api", tags=["export"])

# Diretório base para os uploads na nuvem
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
if IS_VERCEL:
    UPLOAD_DIR = Path("/tmp/AuditoriaTA/uploads")
else:
    UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/auditorias")
async def criar_auditoria(
    unidade: str = Form(...),
    area: str = Form(...),
    ciclo: str = Form(...),
    openai_api_key: str = Form(""),
    observacoes: str = Form(""),
    modo_analise: str = Form("completo"),
    assessment_file: UploadFile = File(None),
    assessment_url: str = Form(""),
    evidence_zip: UploadFile = File(None),
    evidence_url: str = Form("")
):
    """Create a new audit, supporting cloud uploads."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO auditorias
                    (unidade, area, ciclo, data_criacao, data_atualizacao,
                     status, assessment_file_path, evidence_folder_path,
                     openai_api_key, observacoes, modo_analise)
                VALUES (?,?,?,?,?,'em_andamento','','',?,?,?)
            """, (unidade, area, ciclo, now, now,
                  openai_api_key, observacoes, modo_analise))
            row = conn.execute(
                "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
                (unidade, area, ciclo)
            ).fetchone()
            audit_id = row["id"] if row else None
        except Exception:
            row = conn.execute(
                "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
                (unidade, area, ciclo)
            ).fetchone()
            audit_id = row["id"] if row else None

    if not audit_id:
        raise HTTPException(status_code=500, detail="Falha ao criar auditoria")

    # Handle file uploads (local or URL)
    audit_dir = UPLOAD_DIR / str(audit_id)
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    assessment_path = ""
    evidence_path = ""
    
    # 1. Process Assessment File (Excel)
    if assessment_file and assessment_file.filename:
        file_path = audit_dir / f"assessment_{audit_id}.xlsx"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(assessment_file.file, buffer)
        assessment_path = str(file_path.absolute())
    elif assessment_url:
        if os.path.isabs(assessment_url) and os.path.exists(assessment_url):
            # It's a local file from direct upload
            file_path = audit_dir / f"assessment_{audit_id}.xlsx"
            shutil.move(assessment_url, file_path)
            assessment_path = str(file_path.absolute())
        else:
            import urllib.request
            try:
                file_path = audit_dir / f"assessment_{audit_id}.xlsx"
                urllib.request.urlretrieve(assessment_url, file_path)
                assessment_path = str(file_path.absolute())
            except Exception as e:
                print(f"Failed to download assessment from URL: {e}")

    # 2. Process Evidence ZIP
    if evidence_zip and evidence_zip.filename:
        zip_path = audit_dir / f"evidences_{audit_id}.zip"
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(evidence_zip.file, buffer)
        
        extract_dir = audit_dir / "evidences"
        try:
            from backend.routers.evidencias import extract_zip_robustly
            extract_zip_robustly(zip_path, extract_dir)
            evidence_path = str(extract_dir.absolute())
        except Exception as e:
            print(f"Failed to extract uploaded zip: {e}")
            evidence_path = str(extract_dir.absolute())
    elif evidence_url:
        if os.path.isabs(evidence_url) and os.path.exists(evidence_url):
            # It's a local file from direct upload
            zip_path = audit_dir / f"evidences_{audit_id}.zip"
            shutil.move(evidence_url, zip_path)
            
            extract_dir = audit_dir / "evidences"
            from backend.routers.evidencias import extract_zip_robustly
            extract_zip_robustly(zip_path, extract_dir)
            evidence_path = str(extract_dir.absolute())
        else:
            import urllib.request
            try:
                zip_path = audit_dir / f"evidences_{audit_id}.zip"
                urllib.request.urlretrieve(evidence_url, zip_path)
                
                extract_dir = audit_dir / "evidences"
                from backend.routers.evidencias import extract_zip_robustly
                extract_zip_robustly(zip_path, extract_dir)
                evidence_path = str(extract_dir.absolute())
            except Exception as e:
                print(f"Failed to download/extract evidence from URL: {e}")
                evidence_path = evidence_url # Fallback to URL string if extraction fails

    # Update audit record with actual paths and initial evidence map
    evidence_map = {}
    if evidence_path and Path(evidence_path).is_dir():
        try:
            from backend.routers.evidencias import _get_or_build_evidence_map
            evidence_map = _get_or_build_evidence_map(evidence_path, refresh=True)
            # Standardize keys for JSON (tuple -> "P.S")
            evidence_map = {f"{p}.{s}": files for (p, s), files in evidence_map.items()}
        except Exception as e:
            print(f"Failed to build initial evidence map: {e}")

    with get_db() as conn:
        if USE_POSTGRES:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=%s, evidence_folder_path=%s, evidence_map=%s, evidence_zip_url=%s
                WHERE id=%s
            """, (assessment_path, evidence_path, json.dumps(evidence_map), evidence_url or "", audit_id))
        else:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=?, evidence_folder_path=?, evidence_map=?, evidence_zip_url=?
                WHERE id=?
            """, (assessment_path, evidence_path, json.dumps(evidence_map), evidence_url or "", audit_id))

    # 3. Always Populate Subitems from Checklist Baseline
    try:
        from checklist_po_aut_002 import CHECKLIST
        # Determine if we need ON CONFLICT (Postgres) or INSERT OR IGNORE (SQLite)
        insert_sql = """
            INSERT INTO avaliacoes
                (auditoria_id, pratica_num, pratica_nome,
                 subitem_idx, subitem_nome, evidencia_descricao,
                 decisao)
            VALUES (?,?,?,?,?,?,'pendente')
        """
        if USE_POSTGRES:
            insert_sql += " ON CONFLICT (auditoria_id, pratica_num, subitem_idx) DO NOTHING"
        else:
            insert_sql = insert_sql.replace("INSERT INTO", "INSERT OR IGNORE INTO")

        with get_db() as conn:
              # Practice names for display
            pratica_nomes = {
                1: "Rotinas de TA",
                2: "Sobressalentes",
                3: "Mapa de Ativos",
                4: "Disseminação do Conhecimento",
                5: "Gestão de Infraestrutura",
                6: "Gestão de Riscos",
                7: "Interface com a TI",
                8: "Recursos de Software e Hardware",
                9: "CYBERSEGURANÇA"
            }

            subitem_nomes = {
                (1, 0): "Backup Periódico e por Evento",
                (1, 1): "Redundância e Organização",
                (1, 2): "Teste de Backup",
                (1, 3): "Controle de Modificações",
                (1, 4): "Falhas e Alarmes",
                (1, 5): "Verificação de Redes",
                (1, 6): "Manutenção Preventiva",
                (1, 7): "KPI Indisponibilidade",
                (2, 0): "Verificação de Sobressalentes",
                (2, 1): "Equipamentos c/ Sobressalente",
                (3, 0): "Hardware",
                (3, 1): "Software",
                (4, 0): "Treinamentos Equipe",
                (4, 1): "Treinamentos Responsáveis",
                (4, 2): "Boas Práticas",
                (5, 0): "Nobreak",
                (5, 1): "Lista de IPs e IO",
                (5, 2): "Diagramas",
                (5, 3): "Ciclo de Vida",
                (6, 0): "Identificação de Riscos",
                (6, 1): "Planos de Contingência",
                (7, 0): "Fronteiras de Responsabilidade",
                (7, 1): "Projetos Integrados",
                (8, 0): "Eng. Clients e IHM",
                (8, 1): "Servidores",
                (8, 2): "Teste Redundância",
                (8, 3): "Softwares",
                (9, 0): "Treinamento Cyber",
                (9, 1): "Acesso Remoto",
                (9, 2): "Backup Cyber",
                (9, 3): "Resposta a Incidentes",
                (9, 4): "Atualização",
                (9, 5): "Gestão de Acesso",
                (9, 6): "Mídias Removíveis"
            }

            for key, info in CHECKLIST.items():
                p_num, s_idx = key
                p_nome = pratica_nomes.get(p_num, f"Prática {p_num}")
                s_nome = subitem_nomes.get(key, f"Subitem {s_idx}")
                
                conn.execute(insert_sql, (
                    audit_id, p_num, p_nome, s_idx, s_nome, 
                    " \n".join(info.get("verificar", []))
                ))
    except Exception as e:
        print(f"Error populating default checklist: {e}")
        # In production, we want to know if this failed
        if USE_POSTGRES: raise

    # 4. Optional: Parse assessment file to update notas SA if Excel exists
    if assessment_path and Path(assessment_path).exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(assessment_path, data_only=True)
            ws = wb.active
            with get_db() as conn:
                current_p_num = None
                s_idx_internal = 0
                for row_cells in ws.iter_rows(min_row=2, values_only=True):
                    if not any(row_cells): continue
                    
                    if row_cells[0] and str(row_cells[0]).strip().isdigit():
                        current_p_num = int(row_cells[0])
                        s_idx_internal = 0
                    elif current_p_num is not None and row_cells[1]:
                        nota_sa = _safe_int(row_cells[-1])
                        conn.execute("""
                            UPDATE avaliacoes
                            SET nota_self_assessment=?
                            WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
                        """, (nota_sa, audit_id, current_p_num, s_idx_internal))
                        s_idx_internal += 1
        except Exception as e:
            print(f"Failed to parse Excel for SA notes: {e}")

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
