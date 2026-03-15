"""
routers/evidencias.py — Evidence file listing, serving, and criteria retrieval.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from backend.db import get_auditoria, BASE_DIR
import sys
import re
import os
import urllib.parse
import urllib.request
import zipfile
import shutil
import logging

log = logging.getLogger("auditoria_evidencias")

_parent = str(Path(__file__).resolve().parent.parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

router = APIRouter(prefix="/api/evidencias", tags=["evidencias"])

EXTS_IMG = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
EXTS_DOC = {'.pdf', '.xlsx', '.xls', '.docx', '.doc'}
EXTS_VIDEO = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
EXTS_ALL = EXTS_IMG | EXTS_DOC | EXTS_VIDEO


# Caching evidence maps
_EVIDENCE_CACHE = {}

def extract_zip_robustly(zip_path: Path, extract_to: Path):
    """Extract zip and bypass single root folder if present, handling encoding issues."""
    extract_to.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            # Tentar corrigir encoding se o nome parecer CP437 (comum em ZIPs de Windows sem bit UTF-8)
            try:
                # Se o nome original vier como CP437, tentamos converter para UTF-8 se contiver caracteres estendidos
                filename = member.filename
                try:
                    # O zipfile do Python tenta decodar CP437 se não houver flag UTF-8. 
                    # Se decodou algo com caracteres especiais que parecem CP437, re-decodamos.
                    filename = filename.encode('cp437').decode('utf-8')
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
    Checks if a requested path exists. If not, attempts to remap it to the 
    local 'uploads' directory if it belongs to an audit, and triggers 
    lazy restoration (ZIP download/extract) if needed.
    """
    if requested_path.exists():
        return requested_path
        
    log.info(f"File missing: {requested_path}. Attempting to resolve...")
    
    # 1. Detect Audit ID if not provided
    if not audit_id:
        parts = requested_path.parts
        try:
            if "uploads" in parts:
                idx = parts.index("uploads")
                audit_id = int(parts[idx+1])
            else:
                # Identification by prefix matching
                from backend.db import listar_auditorias
                all_audits = listar_auditorias()
                path_str_norm = str(requested_path.absolute()).lower().replace("\\", "/")
                for a in all_audits:
                    fp = a.get("evidence_folder_path")
                    if fp:
                        fp_norm = str(Path(fp).absolute()).lower().replace("\\", "/")
                        if path_str_norm.startswith(fp_norm):
                            audit_id = a["id"]
                            break
        except: pass

    if not audit_id:
        return requested_path 
        
    # 2. Get Audit Data
    aud = get_auditoria(audit_id)
    if not aud:
        return requested_path
        
    # 3. Handle Remapping (Local Path -> Server Uploads)
    server_path = requested_path
    folder_db = aud.get("evidence_folder_path")
    
    if folder_db:
        path_str = str(requested_path.absolute()).replace("\\", "/")
        folder_db_norm = str(Path(folder_db).absolute()).replace("\\", "/")
        if path_str.lower().startswith(folder_db_norm.lower()):
            rel_path = path_str[len(folder_db_norm):].lstrip("/")
            # Garanto que rel_path use separadores do SO atual
            rel_path_obj = Path(rel_path.replace("\\", "/"))
            server_path = BASE_DIR / "uploads" / str(audit_id) / "evidences" / rel_path_obj

    # 4. Lazy Restoration if Server Path missing
    if not server_path.exists() and aud.get("evidence_zip_url"):
        zip_url = aud["evidence_zip_url"]
        audit_dir = BASE_DIR / "uploads" / str(audit_id)
        zip_path = audit_dir / f"evidences_{audit_id}.zip"
        extract_dir = audit_dir / "evidences"
        
        try:
            log.info(f"Restoring audit {audit_id} from {zip_url}...")
            audit_dir.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(zip_url, zip_path)
            extract_zip_robustly(zip_path, extract_dir)
            log.info(f"Restoration complete.")
        except Exception as e:
            log.error(f"Restoration failed for audit {audit_id}: {e}")
            
    return server_path

def _get_or_build_evidence_map(ev_folder: str, refresh: bool = False, aud: dict = None) -> dict:
    """Get from cache or build and cache evidence map. Fallbacks to DB if folder missing."""
    if not ev_folder or not Path(ev_folder).is_dir():
        # Fallback to DB if we have the audit dict
        if aud and aud.get("evidence_map"):
            try:
                import json
                db_map = json.loads(aud["evidence_map"])
                # Convert "1.0" string keys back to (1, 0) tuples
                return {tuple(map(int, k.split('.'))): v for k, v in db_map.items()}
            except Exception as e:
                print(f"Error parsing DB evidence_map: {e}")
        return {}
    
    if ev_folder in _EVIDENCE_CACHE and not refresh:
        return _EVIDENCE_CACHE[ev_folder]
    
    mapa = {}
    try:
        root = Path(ev_folder)
        # Bypassing single root folder wrapper (common in ZIPs)
        items = [i for i in root.iterdir() if not i.name.startswith('.')]
        if len(items) == 1 and items[0].is_dir():
            log.info(f"Bypassing root folder wrapper: {items[0].name}")
            root = items[0]
            
        for pasta_pratica in sorted(root.iterdir()):
            if not pasta_pratica.is_dir():
                continue
            m_p = re.match(r'^\[?(\d+)[\]\-_\s\.]', pasta_pratica.name)
            if not m_p:
                continue
            p_num = int(m_p.group(1))
            
            for pasta_sub in sorted(pasta_pratica.iterdir()):
                if not pasta_sub.is_dir():
                    continue
                m_s = re.match(r'^(\d+)\.(\d+)(?:[\s\-_\.]|$)', pasta_sub.name)
                if not m_s:
                    continue
                s_num = int(m_s.group(2)) - 1  # 0-based
                
                arquivos = [
                    str(f) for f in sorted(pasta_sub.rglob("*"))
                    if f.is_file() and f.suffix.lower() in EXTS_ALL
                ]
                mapa[(p_num, s_num)] = arquivos
        
        _EVIDENCE_CACHE[ev_folder] = mapa
    except Exception as e:
        print(f"Erro ao escanear evidências em {ev_folder}: {e}")
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
    mapa = _get_or_build_evidence_map(ev_folder, refresh=refresh, aud=aud)
    
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
def list_evidences(auditoria_id: int, pratica_num: int, subitem_idx: int):
    """List evidence files for a specific subitem."""
    aud = get_auditoria(auditoria_id)
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")

    # Visibility Rule: Only show evidence if audit is "em_andamento"
    status_norm = str(aud.get("status") or "").lower().strip().replace(" ", "_")
    if status_norm != "em_andamento":
        return {}

    ev_folder = aud.get("evidence_folder_path", "") or ""
    mapa = _get_or_build_evidence_map(ev_folder, aud=aud)
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
        log.info(f"Serve request: path='{path}' -> decoded='{decoded_path}' -> exists={file_path.exists()}")
        
        # 1. Extract audit_id and check visibility
        parts = file_path.parts
        audit_id = None
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
            log.warning(f"File not found on disk: {file_path}")
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

        return FileResponse(
            str(file_path),
            media_type=media_types.get(ext, 'application/octet-stream'),
            filename=file_path.name,
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
    file_path = Path(decoded_path)
    
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

