from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from backend.db import get_auditoria, BASE_DIR, get_db, USE_POSTGRES
import sys
import re
import os
import json
import urllib.parse
import urllib.request
import zipfile
import shutil
import logging
import unicodedata

log = logging.getLogger("auditoria_evidencias")

def _normalize_name(name: str) -> str:
    """Normalize string for soft comparison: lowercase and no accents."""
    try:
        # Standardize characters and remove accents
        nfkd_form = unicodedata.normalize('NFKD', name)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()
    except:
        return name.lower().strip()

_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api/evidencias", tags=["evidencias"])

EXTS_IMG = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
EXTS_DOC = {'.pdf', '.xlsx', '.xls', '.docx', '.doc'}
EXTS_VIDEO = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
EXTS_ALL = EXTS_IMG | EXTS_DOC | EXTS_VIDEO


# Evidence maps are now read from disk/DB to ensure consistency across workers

def extract_zip_robustly(zip_path: Path, extract_to: Path):
    """Extract zip and bypass single root folder if present, handling encoding issues."""
    extract_to.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            try:
                filename = member.filename
                try:
                    # O zipfile do Python tenta decodar CP437 se não houver flag UTF-8. 
                    # No Brasil, é comum ser CP850. Tentamos re-decodar.
                    if any(ord(c) > 127 for c in filename):
                        filename = filename.encode('cp437').decode('cp850')
                except:
                    pass
                
                target_path = extract_to / filename
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
            except Exception as e:
                log.warning(f"Failed to extract {member.filename} with robust encoding: {e}")
                # Fallback simples
                zip_ref.extract(member, extract_to)
    
    # Check for single root folder
    # Ignorar pastas ocultas e o próprio diretório
    items = [i for i in extract_to.iterdir() if not i.name.startswith('.') and i.is_dir()]
    # Se só sobrou uma pasta (e talvez arquivos soltos de sistema), bypass nela
    if len(items) == 1:
        root_folder = items[0]
        log.info(f"Robust Extract: Bypassing root folder {root_folder.name}")
        
        # Mover conteúdo da subpasta para a raiz
        for sub_item in root_folder.iterdir():
            dest = extract_to / sub_item.name
            if dest.exists():
                if dest.is_dir(): shutil.rmtree(dest)
                else: dest.unlink()
            shutil.move(str(sub_item), str(dest))
            
        # Remover a pasta agora vazia
        try:
            shutil.rmtree(root_folder)
        except:
            pass

def resolve_and_ensure_path(requested_path: Path, audit_id: int = None) -> Path:
    """
    Checks if a requested path exists. If not, attempts to remap it and 
    triggers lazy restoration or recursive fuzzy matching to resolve encoding issues.
    """
    if requested_path.exists():
        return requested_path
        
    # 1. Detect Audit ID if not provided
    if not audit_id:
        parts = requested_path.parts
        try:
            if "uploads" in parts:
                idx = parts.index("uploads")
                audit_id = int(parts[idx+1])
        except: pass

    if not audit_id:
        return requested_path 
        
    # 2. Get Audit Data and determine server base
    aud = get_auditoria(audit_id)
    if not aud:
        return requested_path
    
    # Map to server internal uploads folder
    folder_db = aud.get("evidence_folder_path")
    server_base = BASE_DIR / "uploads" / str(audit_id) / "evidences"
    
    # Determine the relative path from the designated evidence root
    rel_path_str = ""
    if folder_db:
        path_str_norm = str(requested_path.absolute()).replace("\\", "/").lower()
        folder_db_norm = str(Path(folder_db).absolute()).replace("\\", "/").lower()
        if path_str_norm.startswith(folder_db_norm):
            rel_path_str = str(requested_path.absolute()).replace("\\", "/")[len(folder_db_norm):].lstrip("/")
    
    if not rel_path_str:
        # If we can't determine rel_path from folder_db, maybe it's already an 'uploads' path
        parts = list(requested_path.parts)
        if "evidences" in parts:
            idx = parts.index("evidences")
            rel_path_str = "/".join(parts[idx+1:])

    # 3. Check for Lazy Restoration if the entire evidences folder is missing
    if not server_base.exists() and aud.get("evidence_zip_url"):
        zip_url = aud["evidence_zip_url"]
        zip_path = (BASE_DIR / "uploads" / str(audit_id)) / f"evidences_{audit_id}.zip"
        try:
            log.info(f"Restoring audit {audit_id} from {zip_url}...")
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            if zip_url.startswith("http"):
                urllib.request.urlretrieve(zip_url, zip_path)
            elif os.path.exists(zip_url):
                shutil.copy2(zip_url, zip_path)
            extract_zip_robustly(zip_path, server_base)
        except Exception as e:
            log.error(f"Restoration failed for audit {audit_id}: {e}")

    # 4. Recursive Fuzzy Matching (Component by Component)
    # Start from a known existing root
    current_path = server_base
    if not current_path.exists():
        return requested_path # Can't even find the base evidence folder
        
    path_components = [p for p in rel_path_str.replace("\\", "/").split("/") if p]
    
    for comp in path_components:
        next_step = current_path / comp
        if next_step.exists():
            current_path = next_step
        else:
            # Fuzzy skip: look for a component that matches after normalization
            found = False
            norm_target = _normalize_name(comp)
            try:
                for item in current_path.iterdir():
                    if _normalize_name(item.name) == norm_target:
                        log.info(f"Fuzzy Match: '{item.name}' instead of '{comp}'")
                        current_path = item
                        found = True
                        break
            except Exception as e:
                log.debug(f"Iterdir failed for {current_path}: {e}")
            
            if not found:
                # If we can't find even a fuzzy match, we must stop and return this broken path
                return current_path / comp
                
    return current_path


def _get_or_build_evidence_map(ev_folder: str, refresh: bool = False, audit: dict = None) -> dict:
    """Get from cache or build and cache evidence map. Fallbacks to DB if folder missing."""
    if not ev_folder or not Path(ev_folder).is_dir():
        # Fallback to DB if we have the audit dict
        if audit and audit.get("evidence_map"):
            try:
                import json
                db_map = json.loads(audit["evidence_map"])
                log.info(f"[SCAN] Using DB fallback for {audit.get('id')}")
                return {tuple(map(int, k.split('.'))): v for k, v in db_map.items()}
            except Exception as e:
                log.error(f"[SCAN] Error parsing DB evidence_map: {e}")
        return {}
    
    mapa = {}
    try:
        root = Path(ev_folder)
        log.info(f"[SCAN] Scanning root: {root.absolute()}")
        
        # Bypassing single root folder wrapper (common in ZIPs)
        items = [i for i in root.iterdir() if not i.name.startswith('.')]
        if len(items) == 1 and items[0].is_dir():
            # Only bypass if it's NOT a practice folder format
            if not re.match(r'^\[?(\d+)[\]\-_\s\.]', items[0].name):
                log.info(f"[SCAN] Bypassing root folder wrapper: {items[0].name}")
                root = items[0]
            
        for pasta_pratica in sorted(root.iterdir()):
            if not pasta_pratica.is_dir(): continue
            m_p = re.match(r'^\[?(\d+)[\]\-_\s\.]', pasta_pratica.name)
            if not m_p:
                log.debug(f"[SCAN]  Skipping dir: {pasta_pratica.name}")
                continue
            
            p_num = int(m_p.group(1))
            log.info(f"[SCAN] Found Practice {p_num}: {pasta_pratica.name}")
            
            for pasta_sub in sorted(pasta_pratica.iterdir()):
                if not pasta_sub.is_dir(): continue
                m_s = re.match(r'^(\d+)\.(\d+)(?:[\s\-_\.]|$)', pasta_sub.name)
                if not m_s:
                    log.debug(f"[SCAN]    Subitem regex NO match: {pasta_sub.name}")
                    continue
                
                s_num = int(m_s.group(2)) - 1  # 0-based
                
                # Scan ALL files first, then filter, for better logging
                all_files = list(pasta_sub.rglob("*"))
                log.info(f"[SCAN]    Subitem {p_num}.{s_num+1} ({pasta_sub.name}) has {len(all_files)} total nodes.")
                
                arquivos = []
                for f in sorted(all_files):
                    if f.is_file():
                        if f.suffix.lower() in EXTS_ALL:
                            arquivos.append(str(f.absolute()))
                        else:
                            log.debug(f"[SCAN]      Ignoring file (ext): {f.name}")
                
                if arquivos:
                    log.info(f"[SCAN]    Subitem {p_num}.{s_num+1} -> {len(arquivos)} valid evidence files.")
                    mapa[(p_num, s_num)] = arquivos
                else:
                    log.warning(f"[SCAN]    Subitem {p_num}.{s_num+1} -> ZERO valid evidence files found.")
        
    except Exception as e:
        log.error(f"[SCAN] Error scanning evidences in {ev_folder}: {e}")
        return {}
        
    return mapa


@router.get("/criterios/all")
def get_all_criterios():
    """Get all criteria for all subitems."""
    from criterios_oficiais import CRITERIOS
    # Convert keys from (P, S) tuple to "P.S" string for JSON
    return {f"{p}.{s}": data for (p, s), data in CRITERIOS.items()}

@router.get("/criterios/{pratica_num}/{subitem_idx}")
def get_criterios(pratica_num: int, subitem_idx: int):
    """Get PO.AUT.002 criteria for a subitem."""
    result = {
        "pratica": "",
        "subitem": "",
        "descricao": "",
        "niveis": {},
        "evidencias_exigidas": "",
        "regras_especiais": "",
        "regras_gerais": "",
        "checklist": {
            "verificar": [],
            "armadilhas": [],
            "nota4": "",
            "regras": [],
            "hard_rule": None,
        }
    }

    try:
        from criterios_oficiais import get_criterio, REGRAS_GERAIS
        crit = get_criterio(pratica_num, subitem_idx)
        result["pratica"] = crit.get("pratica", "") or ""
        result["subitem"] = crit.get("subitem", "") or ""
        result["descricao"] = crit.get("descricao", "") or ""
        result["niveis"] = crit.get("niveis", {}) or {}
        result["evidencias_exigidas"] = crit.get("evidencias_exigidas", "") or ""
        result["regras_especiais"] = crit.get("regras_especiais", "") or ""
        result["regras_gerais"] = REGRAS_GERAIS or ""
    except Exception:
        pass

    try:
        from checklist_po_aut_002 import get_checklist
        ck = get_checklist(pratica_num, subitem_idx)
        result["checklist"] = {
            "verificar": ck.get("verificar", []) or [],
            "armadilhas": ck.get("armadilhas", []) or [],
            "nota4": ck.get("nota4", "") or "",
            "regras": ck.get("regras", []) or [],
            "hard_rule": ck.get("hard_rule"),
        }
    except Exception:
        pass

    return result


@router.get("/audit/{auditoria_id}/all")
def get_all_evidences(auditoria_id: int, refresh: bool = False):
    """Get the entire evidence map for an audit, formatted for frontend."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    # Visibility Rule: Only show evidence if audit is "em_andamento"
    status_norm = str(aud.get("status") or "").lower().strip().replace(" ", "_")
    if status_norm != "em_andamento":
        return {}

    ev_folder = aud.get("evidence_folder_path", "") or ""
    mapa = _get_or_build_evidence_map(ev_folder, refresh=refresh, audit=aud)
    
    # Format map for frontend (keys as strings "P.S")
    formatted = {}
    for (p, s), files in mapa.items():
        images = [f for f in files if Path(f).suffix.lower() in EXTS_IMG]
        docs = [f for f in files if Path(f).suffix.lower() in EXTS_DOC]
        videos = [f for f in files if Path(f).suffix.lower() in EXTS_VIDEO]
        
        formatted[f"{p}.{s}"] = {
            "total": len(files),
            "images": [{"path": f, "name": Path(f).name} for f in images],
            "docs": [{"path": f, "name": Path(f).name} for f in docs],
            "videos": [{"path": f, "name": Path(f).name} for f in videos],
        }
        
    return formatted

@router.get("/{auditoria_id}/{pratica_num}/{subitem_idx}")
def list_evidences(auditoria_id: int, pratica_num: int, subitem_idx: int, refresh: bool = False):
    """List evidence files for a specific subitem."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    # Visibility Rule: Only show evidence if audit is "em_andamento"
    status_norm = str(aud.get("status") or "").lower().strip().replace(" ", "_")
    if status_norm != "em_andamento":
        return {}

    ev_folder = aud.get("evidence_folder_path", "") or ""
    mapa = _get_or_build_evidence_map(ev_folder, refresh=refresh, audit=aud)
    files = mapa.get((pratica_num, subitem_idx), [])

    images = [f for f in files if Path(f).suffix.lower() in EXTS_IMG]
    docs = [f for f in files if Path(f).suffix.lower() in EXTS_DOC]
    videos = [f for f in files if Path(f).suffix.lower() in EXTS_VIDEO]

    return {
        "total": len(files),
        "images": [{"path": f, "name": Path(f).name} for f in images],
        "docs": [{"path": f, "name": Path(f).name} for f in docs],
        "videos": [{"path": f, "name": Path(f).name} for f in videos],
        "ev_folder": ev_folder,
    }


@router.get("/file")
def serve_file(path: str = Query(..., description="Absolute path to the evidence file")):
    """
    Serve an evidence file (image, PDF, video, document).
    The path must be an absolute path to a file on disk.
    """
    try:
        decoded_path = urllib.parse.unquote(path)
        file_path = Path(decoded_path)
        
        # 1. Extract audit_id and check visibility
        parts = file_path.parts
        audit_id = None
        log.info(f"Serve request: path='{path}' -> decoded='{decoded_path}'")
        # Identification Logic (Reuse the logic to get audit_id for security check)
        try:
            if "uploads" in parts:
                idx = parts.index("uploads")
                audit_id = int(parts[idx+1])
            else:
                from backend.db import listar_auditorias
                all_audits = listar_auditorias()
                path_str_norm = str(file_path.absolute()).lower().replace("\\", "/")
                for a in all_audits:
                    fp = a.get("evidence_folder_path")
                    if fp:
                        fp_norm = str(Path(fp).absolute()).lower().replace("\\", "/")
                        if path_str_norm.startswith(fp_norm):
                            audit_id = a["id"]
                            break
            
            if audit_id:
                aud = get_auditoria(audit_id)
                status_norm = str(aud.get("status") or "").lower().strip().replace(" ", "_")
                if status_norm != "em_andamento":
                    raise HTTPException(status_code=403, detail=f"Acesso negado: Auditoria '{aud.get('unidade')}' não está mais em andamento.")
        except (ValueError, IndexError):
            pass

        # 2. Resolve Path and Ensure local existence (Magic happening here)
        file_path = resolve_and_ensure_path(file_path, audit_id)

        if not file_path.exists():
            log.warning(f"File not found on disk: {file_path} (Requested: {path})")
            # Log siblings to help identify encoding mismatches
            if file_path.parent.exists():
                try:
                    siblings = [f.name for f in file_path.parent.iterdir()][:10]
                    log.info(f"Siblings of missing file: {siblings}")
                except: pass
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {decoded_path}")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Caminho não é um arquivo")

        ext = file_path.suffix.lower()
        if ext not in {e.lower() for e in EXTS_ALL}:
            raise HTTPException(status_code=400, detail=f"Tipo de arquivo não suportado: {ext}")

        media_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.bmp': 'image/bmp', '.webp': 'image/webp',
            '.pdf': 'application/pdf',
            '.mp4': 'video/mp4', '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime', '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
        }

        # For images, PDFs, and videos: serve inline so browsers can render in <img>/<video>/<object> tags
        # For documents (xlsx, docx): serve as attachment (download)
        inline_types = EXTS_IMG | EXTS_VIDEO | {'.pdf'}
        disposition = "inline" if ext in inline_types else "attachment"

        return FileResponse(
            str(file_path),
            media_type=media_types.get(ext, 'application/octet-stream'),
            filename=file_path.name,
            content_disposition_type=disposition,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error serving file {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/preview")
def preview_document(path: str = Query(..., description="Absolute path to the document")):
    """
    Preview a document inline. Returns rendered content based on file type:
    - PDF: base64-encoded data for <object> embed
    - XLSX/XLS: HTML table from first sheet
    - DOCX/DOC: extracted text paragraphs
    """
    decoded_path = urllib.parse.unquote(path)
    # Check if still looks URL-encoded (has % followed by hex)
    if "%" in decoded_path:
        try:
            # Try second pass unquote if it looks like double encoded
            if re.search(r'%[0-9a-fA-F]{2}', decoded_path):
                decoded_path = urllib.parse.unquote(decoded_path)
        except: pass

    file_path = Path(decoded_path)
    log.info(f"Preview request: path='{path}' -> decoded='{decoded_path}'")
    
    # Extract audit_id from path and check visibility
    parts = file_path.parts
    audit_id = None
    try:
        if "uploads" in parts:
            idx = parts.index("uploads")
            audit_id = int(parts[idx+1])
        else:
            # Robust detection for local/absolute paths
            from backend.db import listar_auditorias
            all_audits = listar_auditorias()
            path_str_norm = str(file_path.absolute()).lower().replace("\\", "/")
            for a in all_audits:
                fp = a.get("evidence_folder_path")
                if fp:
                    fp_norm = str(Path(fp).absolute()).lower().replace("\\", "/")
                    if path_str_norm.startswith(fp_norm):
                        audit_id = a["id"]
                        break
        
        if audit_id:
            aud = get_auditoria(audit_id)
            status_norm = str(aud.get("status") or "").lower().strip().replace(" ", "_")
            if status_norm != "em_andamento":
                raise HTTPException(status_code=403, detail="Acesso negado: Auditoria não em andamento.")
    except (ValueError, IndexError):
        pass

    # Resolve Path and Ensure local existence
    file_path = resolve_and_ensure_path(file_path, audit_id)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    ext = file_path.suffix.lower()

    # ── PDF: return base64 for inline embed ──
    if ext == '.pdf':
        import base64
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return {
            "type": "pdf",
            "name": file_path.name,
            "data": data,
        }

    # ── Excel: convert first sheet to HTML table ──
    if ext in {'.xlsx', '.xls'}:
        try:
            import pandas as pd
            df = pd.read_excel(file_path, sheet_name=0)
            # Limit to first 200 rows to avoid huge responses
            if len(df) > 200:
                df = df.head(200)
            html_table = df.to_html(
                index=False,
                classes="ev-table",
                border=0,
                na_rep="—",
            )
            return {
                "type": "excel",
                "name": file_path.name,
                "html": html_table,
                "rows": len(df),
                "cols": len(df.columns),
            }
        except Exception as e:
            return {"type": "error", "name": file_path.name, "error": str(e)}

    # ── Word: extract paragraphs as text ──
    if ext in {'.docx', '.doc'}:
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return {
                "type": "word",
                "name": file_path.name,
                "paragraphs": paragraphs,
            }
        except Exception as e:
            return {"type": "error", "name": file_path.name, "error": str(e)}


    return {"type": "unsupported", "name": file_path.name}


@router.post("/upload-granular")
async def upload_granular(
    auditoria_id: int = Form(...),
    pratica_num: int = Form(...),
    subitem_idx: int = Form(...),
    file: UploadFile = File(...)
):
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    
    # 1. Definir Pasta Alvo
    # Usamos o caminho padrão: uploads/{audit_id}/evidences/Pratica {num}/Subitem {idx+1}/
    audit_dir = BASE_DIR / "uploads" / str(auditoria_id)
    evidences_dir = audit_dir / "evidences"
    
    # Formatação de pasta para manter compatibilidade com o construtor do mapa
    # O mapa busca por "[1] NOME" ou "1. " para prática e "1.1 NOME" para subitem
    p_folder_name = f"[{pratica_num}] Pratica {pratica_num}"
    s_folder_name = f"{pratica_num}.{subitem_idx + 1}"
    
    target_dir = evidences_dir / p_folder_name / s_folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = target_dir / file.filename
    
    # 2. Salvar Arquivo e Extrair se for ZIP
    try:
        if file.filename.lower().endswith(".zip"):
            # Salva temporariamente e extrai
            temp_zip = target_dir / f"temp_{file.filename}"
            with open(temp_zip, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            log.info(f"Extracting granular ZIP: {file.filename}")
            extract_zip_robustly(temp_zip, target_dir)
            temp_zip.unlink() # Remove o zip após extrair
        else:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        log.error(f"Error saving/extracting granular upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
    
    # 3. Atualizar mapa de evidências (background ou imediato)
    try:
        # Re-escaneia a pasta de evidências para o novo mapa
        log.info(f"[UPLOAD] Re-scanning evidence folder for audit {auditoria_id}: {evidences_dir}")
        new_map = _get_or_build_evidence_map(str(evidences_dir), refresh=True)
        
        # Converte chaves para string para salvar no DB
        db_map = {f"{p}.{s}": files for (p, s), files in new_map.items()}
        log.info(f"[UPLOAD] Found {len(db_map)} subitems with evidence in new map: {list(db_map.keys())}")
        
        with get_db() as conn:
            q = "UPDATE auditorias SET evidence_map=?, evidence_folder_path=? WHERE id=?"
            if USE_POSTGRES: q = q.replace("?", "%s")
            conn.execute(q, (json.dumps(db_map), str(evidences_dir), auditoria_id))
            conn.commit()
            
        log.info(f"[UPLOAD] Granular upload success: {file.filename} for audit {auditoria_id}. DB updated.")
    except Exception as e:
        log.error(f"[UPLOAD] Evidence map update failed after upload: {e}")
    
    return {
        "ok": True,
        "filename": file.filename,
        "path": str(file_path),
        "message": "Arquivo enviado com sucesso!"
    }


@router.delete("/remover")
async def remover_evidencia(
    auditoria_id: int = Query(...),
    path: str = Query(...)
):
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    
    try:
        # Decodar o caminho recebido
        decoded_path = urllib.parse.unquote(path)
        file_path = Path(decoded_path).resolve()
        
        if not file_path.exists():
            log.warning(f"Tentativa de remover arquivo inexistente: {file_path}")
            return {"ok": True, "message": "Arquivo já não existe"}
        
        # Segurança: garantir que o arquivo está dentro da pasta de uploads da auditoria
        audit_dir = (BASE_DIR / "uploads" / str(auditoria_id)).resolve()
        
        # Verifica se o arquivo está dentro da pasta da auditoria
        if not str(file_path).startswith(str(audit_dir)):
            log.error(f"Tentativa de violação de segurança: {file_path} não está em {audit_dir}")
            raise HTTPException(status_code=403, detail="Acesso negado: o arquivo não pertence a esta auditoria.")

        if file_path.is_file():
            file_path.unlink()
            log.info(f"Arquivo removido: {file_path}")
        else:
            raise HTTPException(status_code=400, detail="O caminho não é um arquivo")
            
        # Atualizar mapa
        ev_root = audit_dir / "evidences"
        if ev_root.exists():
            new_map = _get_or_build_evidence_map(str(ev_root), refresh=True)
            db_map = {f"{p}.{s}": files for (p, s), files in new_map.items()}
            
            with get_db() as conn:
                q = "UPDATE auditorias SET evidence_map=? WHERE id=?"
                if USE_POSTGRES: q = q.replace("?", "%s")
                conn.execute(q, (json.dumps(db_map), auditoria_id))
                conn.commit()
            
        return {"ok": True, "message": "Arquivo removido com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error removing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/limpar-subitem")
async def limpar_subitem(
    auditoria_id: int = Query(...),
    pratica_num: int = Query(...),
    subitem_idx: int = Query(...)
):
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    
    try:
        # Define the target folder
        ev_root = aud.get("evidence_folder_path")
        if ev_root:
            evidences_dir = Path(ev_root)
        else:
            audit_dir = BASE_DIR / "uploads" / str(auditoria_id)
            evidences_dir = audit_dir / "evidences"
        
        if not evidences_dir.exists():
            return {"ok": True, "message": "Pasta de evidências não encontrada"}

        # 1. Encontrar a pasta da prática (Regex robusto)
        # Padrão: começa com o número da prática opcionalmente entre colchetes, seguido por separador
        p_regex = fr'^\[?{pratica_num}[\]\s\-\._]'
        target_dir = None
        
        for p_folder in evidences_dir.iterdir():
            if p_folder.is_dir() and re.match(p_regex, p_folder.name):
                # 2. Encontrar a pasta do subitem dentro da prática
                # Padrão: X.Y seguido de separador ou fim de string
                s_regex = fr'^{pratica_num}\.{subitem_idx + 1}(?:[\s\-\._]|$)'
                for s_folder in p_folder.iterdir():
                    if s_folder.is_dir() and re.match(s_regex, s_folder.name):
                        target_dir = s_folder
                        break
                if target_dir: break

        if target_dir and target_dir.exists():
            # Delete everything inside target_dir
            shutil.rmtree(str(target_dir))
            log.info(f"Pasta de subitem removida: {target_dir}")
            
            # Recreate the folder (empty)
            target_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Pasta recriada (vazia): {target_dir}")
        else:
            log.warning(f"Pasta de subitem não encontrada para P{pratica_num} S{subitem_idx+1} em {evidences_dir}")
            return {"ok": True, "message": "Pasta já não existe ou está vazia"}
            
        # Atualizar mapa no banco de dados
        new_map = _get_or_build_evidence_map(str(evidences_dir), refresh=True)
        db_map = {f"{p}.{s}": files for (p, s), files in new_map.items()}
        
        with get_db() as conn:
            q = "UPDATE auditorias SET evidence_map=? WHERE id=?"
            if USE_POSTGRES: q = q.replace("?", "%s")
            conn.execute(q, (json.dumps(db_map), auditoria_id))
            conn.commit()
            
        return {"ok": True, "message": "Todas as evidências do subitem foram removidas"}
    except Exception as e:
        log.error(f"Error clearing subitem evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
