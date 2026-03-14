"""
routers/upload.py — Direct file upload to Railway volume.
Alternative to Vercel Blob when suspended.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import shutil
import os
import uuid
import logging

log = logging.getLogger("auditoria_upload")
router = APIRouter(prefix="/api/upload", tags=["upload"])

# Railway volume path
UPLOAD_DIR = Path("/app/data/uploads") if os.path.exists("/app/data") else Path("uploads")

@router.post("/direct")
async def upload_direct(
    file: UploadFile = File(...),
    type: str = Form("evidence"), # evidence or assessment
):
    """Upload a file directly to the server."""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Safe filename
        ext = Path(file.filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = UPLOAD_DIR / unique_name
        
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return a URL that the backend can use (local path for production)
        # Note: In Railway, these files are on local disk.
        # We return the absolute path so the 'creation' logic can move it.
        return {
            "ok": True,
            "url": str(target_path.absolute()),
            "filename": file.filename,
            "size": target_path.stat().st_size
        }
    except Exception as e:
        log.error(f"Direct upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
