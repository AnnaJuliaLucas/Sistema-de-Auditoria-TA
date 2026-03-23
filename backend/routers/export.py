"""
routers/export.py — Excel export and new audit creation.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.db import get_db, get_auditoria, carregar_avaliacoes, _safe_int, USE_POSTGRES
from backend.auth import get_current_user
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
            _parse_assessment_sheet(ws, audit_id)
        except Exception as e:
            log.error(f"Background Excel sync failed for audit {audit_id}: {e}")

def _parse_assessment_sheet(ws, audit_id: int):
    """
    Robustly parses the assessment worksheet to extract SA scores.
    Supports:
    1. Standard Checklist (scores in Col I/J, descriptions in Col C)
    2. Integrated Report (scores in Col B, descriptions in Col A)
    """
    import re
    from backend.db import get_db, _safe_int
    
    current_p_num = None
    s_idx_internal = 0
    updates = []
    is_integrated = False
    
    # Headers to skip
    SKIP_KEYWORDS = {
        "EVIDÊNCIA", "SUBITEM", "DESCRIÇÃO", "PRÁTICA", "REQUISITO", 
        "EVIDENCIAS", "N°", "NÃO TEM PRÁTICA", "PONTUAÇÃO", 
        "STATUS DA NOTA", "TIPO DE NÃO CONFORMIDADE"
    }

    log.info(f"Refined parsing started for audit {audit_id}")

    # 1. Detect format by inspecting the first few rows
    for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
        if not row: continue
        row_str = " ".join(str(c).upper() for c in row if c)
        if "STATUS DA NOTA" in row_str or "COMENTÁRIOS ADICIONAIS" in row_str:
            is_integrated = True
            log.info(f"Audit {audit_id}: Detected 'Integrated Report' format.")
            break

    # 2. Parse rows
    for i, row_cells in enumerate(ws.iter_rows(min_row=1, values_only=True)):
        # Skip completely empty rows
        if not any(c is not None and str(c).strip() != "" for c in row_cells[:10]):
            continue

        first_col = str(row_cells[0] or "").strip()
        second_col = str(row_cells[1] or "").strip()
        third_col = str(row_cells[2] or "").strip() if len(row_cells) > 2 else ""

        # 2a. Practice Detection
        # Standard: "1", "4.1"
        # Integrated: "1 - ROTINAS DE TA"
        p_match = re.search(r'^(\d+)', first_col)
        sub_match = re.search(r'^(\d+)\.(\d+)', first_col)
        
        if p_match and len(first_col) < 30: # Allow longer for "1 - ROTINAS..."
            new_p = int(p_match.group(1))
            
            # If it's a new practice, reset the index
            if new_p != current_p_num:
                # Special case for Integrated: "1 - ROTINAS" row should NOT be a subitem
                # but if Column B has a note, it might be. Usually headers in Integrated have None in Note Col.
                current_p_num = new_p
                s_idx_internal = 0
                log.info(f"Audit {audit_id}: Detected Practice {current_p_num} at row {i+1}")

            # If it's a dot-notation (e.g., "4.1"), accurately set the index
            if sub_match:
                s_idx_internal = int(sub_match.group(2)) - 1
                if s_idx_internal < 0: s_idx_internal = 0

        # 2b. Subitem Identification & Score Extraction
        if current_p_num is not None:
            if is_integrated:
                # Integrated: Description in A, Score in B
                desc = first_col
                nota_sa = _safe_int(row_cells[1]) if len(row_cells) > 1 else None
                
                # Title rows in Integrated have "N - NAME" in Col A and often None in Col B
                # If it matches the practice pattern and has no note, skip as subitem
                if re.search(r'^\d+\s*-\s*', desc) and nota_sa is None:
                    continue
            else:
                # Standard: Description in C (preferred) or B, Score in I/J
                desc = third_col or second_col
                nota_sa = None
                for col_idx in (8, 9, 7, 10):
                    if len(row_cells) > col_idx:
                        val = _safe_int(row_cells[col_idx])
                        if val is not None:
                            nota_sa = val
                            break

            if not desc or len(desc) < 3:
                continue

            desc_upper = desc.upper()
            if any(k in desc_upper for k in SKIP_KEYWORDS):
                continue
                
            # Skip likely Practice Titles
            if not is_integrated:
                if ("PRÁTICA" in str(second_col).upper() or "PS 00" in str(second_col).upper()) and len(desc) < 60:
                    continue

            updates.append((nota_sa, audit_id, current_p_num, s_idx_internal))
            s_idx_internal += 1

    # 3. Apply updates

    # 4. Apply updates
    if updates:
        with get_db() as conn:
            for params in updates:
                conn.execute("""
                    UPDATE avaliacoes
                    SET nota_self_assessment=?
                    WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
                """, params)
            conn.commit()
        log.info(f"Audit {audit_id}: Finished syncing {len(updates)} subitems from Excel.")
    
    return len(updates)

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
    evidence_url: str = Form(""),
    current_user: str = Depends(get_current_user)
):
    """Create audit skeleton and offload processing to background task."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        q = """
            INSERT INTO auditorias
                (unidade, area, ciclo, data_criacao, data_atualizacao,
                 status, assessment_file_path, evidence_folder_path,
                 openai_api_key, observacoes, modo_analise, ai_provider, ai_base_url, auditado_por)
            VALUES (?,?,?,?,?,'em_andamento','','',?,?,?,'','',?)
        """
        if USE_POSTGRES: q = q.replace("?", "%s")
        conn.execute(q, (unidade, area, ciclo, now, now, openai_api_key, observacoes, modo_analise, current_user))
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
        imported = _parse_assessment_sheet(ws, auditoria_id)
        return {"ok": True, "imported": imported}
    except Exception as e:
        log.error(f"Manual import failed for audit {auditoria_id}: {e}")
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
        "Sitrel": ["Laminação"],
        "João Monlevade": ["Aciaria", "Laminação", "Alto Forno", "Utilidades"],
        "Trefilarias": ["São Paulo", "Sabará", "Resende", "Juiz de Fora"],
        "Mina do Andrade": ["Mineração"]
    }
    
