"""
routers/export.py — Excel export and new audit creation.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
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
import logging

log = logging.getLogger("auditoria_export")

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

def process_heavy_files(audit_id: int, assessment_url: str, evidence_url: str, assessment_file_bytes: bytes, evidence_zip_bytes: bytes):
    """Background task to handle heavy file processing without timing out the request."""
    audit_dir = UPLOAD_DIR / str(audit_id)
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    assessment_path = ""
    evidence_path = ""
    
    # 1. Process Assessment
    if assessment_file_bytes:
        file_path = audit_dir / f"assessment_{audit_id}.xlsx"
        with open(file_path, "wb") as buffer:
            buffer.write(assessment_file_bytes)
        assessment_path = str(file_path.absolute())
    elif assessment_url:
        if os.path.isabs(assessment_url) and os.path.exists(assessment_url):
            file_path = audit_dir / f"assessment_{audit_id}.xlsx"
            shutil.copy2(assessment_url, file_path) # Usar copy2 em vez de move para evitar problemas de permissão
            assessment_path = str(file_path.absolute())
        else:
            import urllib.request
            try:
                file_path = audit_dir / f"assessment_{audit_id}.xlsx"
                urllib.request.urlretrieve(assessment_url, file_path)
                assessment_path = str(file_path.absolute())
            except Exception as e:
                log.error(f"Failed to download assessment: {e}")

    # 2. Process Evidence ZIP
    if evidence_zip_bytes:
        zip_path = audit_dir / f"evidences_{audit_id}.zip"
        with open(zip_path, "wb") as buffer:
            buffer.write(evidence_zip_bytes)
        
        extract_dir = audit_dir / "evidences"
        try:
            from backend.routers.evidencias import extract_zip_robustly
            extract_zip_robustly(zip_path, extract_dir)
            evidence_path = str(extract_dir.absolute())
            # Cleanup ZIP after extraction to save space
            if zip_path.exists():
                os.remove(zip_path)
                log.info(f"Removed temporary ZIP: {zip_path}")
        except Exception as e:
            log.error(f"Failed to extract: {e}")
            evidence_path = str(extract_dir.absolute())
    elif evidence_url:
        if os.path.isabs(evidence_url) and os.path.exists(evidence_url):
            zip_path = audit_dir / f"evidences_{audit_id}.zip"
            shutil.copy2(evidence_url, zip_path)
            extract_dir = audit_dir / "evidences"
            try:
                from backend.routers.evidencias import extract_zip_robustly
                extract_zip_robustly(zip_path, extract_dir)
                evidence_path = str(extract_dir.absolute())
            except Exception as e:
                log.error(f"Failed to extract local URL zip: {e}")
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
                # Cleanup ZIP after extraction to save space
                if zip_path.exists():
                    os.remove(zip_path)
                    log.info(f"Removed downloaded ZIP: {zip_path}")
            except Exception as e:
                log.error(f"Failed to download/extract URL zip: {e}")

    # 3. Build Evidence Map
    evidence_map = {}
    if evidence_path and Path(evidence_path).is_dir():
        try:
            from backend.routers.evidencias import _get_or_build_evidence_map
            evidence_map = _get_or_build_evidence_map(evidence_path, refresh=True)
            # Standardize keys for JSON (tuple -> "P.S")
            evidence_map = {f"{p}.{s}": files for (p, s), files in evidence_map.items()}
        except Exception as e:
            log.error(f"Map failed: {e}")

    # 4. Final DB Update (Paths and Evidence Map)
    with get_db() as conn:
        q = "UPDATE auditorias SET assessment_file_path=?, evidence_folder_path=?, evidence_map=?, evidence_zip_url=? WHERE id=?"
        if USE_POSTGRES: q = q.replace("?", "%s")
        conn.execute(q, (assessment_path, evidence_path, json.dumps(evidence_map), evidence_url or "", audit_id))
        conn.commit()

    # 5. Populate Subitems (Baseline)
    try:
        from checklist_po_aut_002 import CHECKLIST
        from criterios_oficiais import CRITERIOS
        with get_db() as conn:
            for key, info in CHECKLIST.items():
                p_num, s_idx = key
                p_nome = "Rotinas de TA" # Default
                
                # Get official names if available
                crit_info = CRITERIOS.get(key, {})
                s_nome = crit_info.get('subitem') or f"Subitem {s_idx+1}"
                p_nome_oficial = crit_info.get('pratica')
                
                # Fallback mapping for practice names
                pratica_nomes = {1:"Rotinas de TA", 2:"Sobressalentes", 3:"Mapa de Ativos", 4:"Conhecimento", 5:"Infraestrutura", 6:"Riscos", 7:"TI", 8:"Software/Hardware", 9:"Cyber"}
                p_nome = p_nome_oficial or pratica_nomes.get(p_num, p_nome)

                q_ins = "INSERT OR IGNORE INTO avaliacoes (auditoria_id, pratica_num, pratica_nome, subitem_idx, subitem_nome, evidencia_descricao, decisao) VALUES (?,?,?,?,?,?,'pendente')"
                if USE_POSTGRES: 
                    q_ins = "INSERT INTO avaliacoes (auditoria_id, pratica_num, pratica_nome, subitem_idx, subitem_nome, evidencia_descricao, decisao) VALUES (%s,%s,%s,%s,%s,%s,'pendente') ON CONFLICT DO NOTHING"
                
                conn.execute(q_ins, (audit_id, p_num, p_nome, s_idx, s_nome, " \n".join(info.get("verificar", []))))
            conn.commit()
    except Exception as e:
        log.error(f"Background baseline population failed: {e}")

    # 6. Parse Excel for SA Notes (Optional)
    if assessment_path and Path(assessment_path).exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(assessment_path, data_only=True)
            ws = wb.active
            with get_db() as conn:
                current_p_num = None
                s_idx_internal = 0
                for row_cells in ws.iter_rows(min_row=2, values_only=True):
                    # Se não tiver absolutamente nada em nenhuma das 9 primeiras colunas, pula.
                    has_content = any(c is not None and str(c).strip() != "" for c in row_cells[:15])
                    if not has_content: continue

                    # Detecta Prática
                    if row_cells[0] and str(row_cells[0]).strip().isdigit():
                        current_p_num = int(row_cells[0])
                        s_idx_internal = 0
                    
                    # Processa Subitem (mesmo se for na mesma linha da Prática)
                    # Usamos a coluna C (índice 2) que contém a descrição do subitem/evidência
                    if current_p_num is not None and len(row_cells) > 2 and row_cells[2]:
                        # Coluna I (índice 8). 
                        if len(row_cells) > 8:
                            val_raw = row_cells[8]
                            is_header_row = False
                            # Ignora se for a linha de cabeçalho "NOTA ITEM" ou similar
                            if val_raw is not None and str(val_raw).strip().upper() == "NOTA ITEM":
                                is_header_row = True
                            if str(row_cells[1]).strip().upper() == "PRÁTICA" or str(row_cells[2]).strip().upper() == "EVIDÊNCIA":
                                is_header_row = True
                                
                            if not is_header_row:
                                nota_sa = _safe_int(val_raw)
                                log.info(f"Audit {audit_id}: P{current_p_num} S{s_idx_internal} -> Raw Col I: '{val_raw}' -> Nota SA: {nota_sa}")
                                conn.execute("""
                                    UPDATE avaliacoes
                                    SET nota_self_assessment=?
                                    WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
                                """, (nota_sa, audit_id, current_p_num, s_idx_internal))
                                s_idx_internal += 1
                conn.commit()
            log.info(f"Background Excel SA sync complete for audit {audit_id}. (Column I used)")
        except Exception as e:
            log.error(f"Background Excel sync failed: {e}")

@router.post("/auditorias")
async def criar_auditoria(
    background_tasks: BackgroundTasks,
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
    """Create audit skeleton and offload processing to background task."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        q = """
            INSERT INTO auditorias
                (unidade, area, ciclo, data_criacao, data_atualizacao,
                 status, assessment_file_path, evidence_folder_path,
                 openai_api_key, observacoes, modo_analise)
            VALUES (?,?,?,?,?,'em_andamento','','',?,?,?)
        """
        if USE_POSTGRES: q = q.replace("?", "%s")
        conn.execute(q, (unidade, area, ciclo, now, now, openai_api_key, observacoes, modo_analise))
        conn.commit()
        
        row = conn.execute("SELECT id FROM auditorias ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Erro ao reservar ID da auditoria")
        audit_id = row["id"]

    # Read bytes to pass to background task (Uvicorn handles large files well, but we must read them before request ends)
    as_bytes = await assessment_file.read() if assessment_file else None
    ev_bytes = await evidence_zip.read() if evidence_zip else None
    
    background_tasks.add_task(
        process_heavy_files, 
        audit_id, assessment_url, evidence_url, as_bytes, ev_bytes
    )

    return {
        "ok": True, 
        "id": audit_id, 
        "message": "Auditoria criada com sucesso! Os arquivos estão sendo processados em segundo plano e as evidências aparecerão em instantes."
    }

@router.post("/auditorias/{auditoria_id}/importar-assessment")
def importar_assessment(auditoria_id: int, assessment_path: str = ""):
    """Manual trigger to re-import assessment Excel."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    path = assessment_path or aud.get("assessment_file_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=400, detail="Arquivo de assessment não encontrado")

    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        imported = 0
        with get_db() as conn:
            current_p_num = None
            s_idx = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not any(row): continue
                # Detecta Prática
                if row[0] and str(row[0]).strip().isdigit():
                    current_p_num = int(row[0])
                    s_idx = 0
                
                # Processa Subitem - Usamos a coluna C (índice 2)
                if current_p_num and row[2]:
                    # Ignorar linha de cabeçalho
                    if str(row[1]).strip().upper() == "PRÁTICA" or str(row[2]).strip().upper() == "EVIDÊNCIA":
                        continue
                        
                    # Coluna I (índice 8)
                    nota_sa = _safe_int(row[8])
                    conn.execute("""
                        UPDATE avaliacoes SET nota_self_assessment=?
                        WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
                    """, (nota_sa, auditoria_id, current_p_num, s_idx))
                    s_idx += 1
                    imported += 1
            conn.commit()
        log.info(f"Manual Excel import complete for audit {auditoria_id}. {imported} items updated (Column I).")
        return {"ok": True, "imported": imported}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao importar: {str(e)}")

@router.get("/auditorias/{auditoria_id}/exportar-excel")
def exportar_excel(auditoria_id: int):
    """Export audit results matching legacy Excel template."""
    aud = get_auditoria(auditoria_id)
    if not aud: raise HTTPException(status_code=404, detail="Não encontrado")
    df = carregar_avaliacoes(auditoria_id)
    
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Análise"
    
    # Simple export (simplified for brevity, keeping main structure)
    ws.append([f"RELATÓRIO DE AUDITORIA - {aud['unidade']} - {aud['area']}"])
    ws.append(["Prática", "Subitem", "Nota SA", "Nota Final", "Decisão", "Comentários"])
    
    for av in df:
        ws.append([av['pratica_nome'], av['subitem_nome'], av['nota_self_assessment'], av['nota_final'], av['decisao'], av['comentarios']])
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    tmp.close()
    return FileResponse(tmp.name, filename=f"Auditoria_{auditoria_id}.xlsx")

@router.get("/unidades-areas")
def get_unidades_areas():
    return {
        "Juiz de Fora": ["Utilidades", "Aciaria", "Laminação", "Redução"],
        "Piracicaba": ["Aciaria", "Utilidades", "Laminação"],
        "João Monlevade": ["Aciaria", "Laminação", "Alto Forno", "Utilidades"],
        "Trefilarias": ["São Paulo", "Sabará", "Resende", "Juiz de Fora"],
        "Mina do Andrade": ["Mineração"]
    }
