"""
routers/evidencias.py — Evidence file listing, serving, and criteria retrieval.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from backend.db import get_auditoria
import sys
import re
import os
import urllib.parse

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

def _get_or_build_evidence_map(ev_folder: str, refresh: bool = False) -> dict:
    """Get from cache or build and cache evidence map."""
    if not ev_folder or not Path(ev_folder).is_dir():
        return {}
    
    if ev_folder in _EVIDENCE_CACHE and not refresh:
        return _EVIDENCE_CACHE[ev_folder]
    
    mapa = {}
    try:
        root = Path(ev_folder)
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

    ev_folder = aud.get("evidence_folder_path", "") or ""
    mapa = _get_or_build_evidence_map(ev_folder, refresh=refresh)
    
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

    ev_folder = aud.get("evidence_folder_path", "") or ""
    mapa = _get_or_build_evidence_map(ev_folder)
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
    # Decode the path in case it was double-encoded
    decoded_path = urllib.parse.unquote(path)
    file_path = Path(decoded_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {decoded_path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Caminho não é um arquivo")

    ext = file_path.suffix.lower()
    if ext not in EXTS_ALL:
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

