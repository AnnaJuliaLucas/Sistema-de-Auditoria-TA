"""
routers/utils.py — Utility endpoints for native UI interactions.
"""
from fastapi import APIRouter, HTTPException
import tkinter as tk
from tkinter import filedialog
import threading
import logging

log = logging.getLogger("auditoria_utils")
router = APIRouter(prefix="/api/utils", tags=["utils"])

def _pick_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Selecione o arquivo de Assessment (Excel)",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    root.destroy()
    return file_path

def _pick_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder_path = filedialog.askdirectory(
        title="Selecione a pasta de evidências"
    )
    root.destroy()
    return folder_path

@router.get("/pick-file")
async def pick_file():
    """Opens a native Windows file picker and returns the selected path."""
    try:
        # Run in a separate thread to avoid blocking the event loop and for Tkinter compatibility
        result = []
        def target():
            result.append(_pick_file())
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        
        path = result[0] if result else ""
        return {"path": path}
    except Exception as e:
        log.error(f"Erro ao abrir seletor de arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pick-folder")
async def pick_folder():
    """Opens a native Windows folder picker and returns the selected path."""
    try:
        result = []
        def target():
            result.append(_pick_folder())
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        
        path = result[0] if result else ""
        return {"path": path}
    except Exception as e:
        log.error(f"Erro ao abrir seletor de pasta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
