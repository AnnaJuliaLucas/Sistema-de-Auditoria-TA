"""
routers/utils.py — Utility endpoints for native UI interactions.
"""
from fastapi import APIRouter, HTTPException
import subprocess
import sys
import logging
import asyncio

log = logging.getLogger("auditoria_utils")
router = APIRouter(prefix="/api/utils", tags=["utils"])

def run_tkinter_script(script_code: str) -> str:
    try:
        # Run tkinter in a completely separate process to avoid thread issues
        result = subprocess.run(
            [sys.executable, "-c", script_code], 
            capture_output=True, 
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        log.error(f"Erro subprocess tkinter: {e}")
        return ""

def _pick_file():
    script = """
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
file_path = filedialog.askopenfilename(
    title="Selecione o arquivo de Assessment (Excel)",
    filetypes=[("Excel files", "*.xlsx *.xls")]
)
root.destroy()
if file_path:
    print(file_path)
"""
    return run_tkinter_script(script)

def _pick_folder():
    script = """
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
folder_path = filedialog.askdirectory(
    title="Selecione a pasta de evidências"
)
root.destroy()
if folder_path:
    print(folder_path)
"""
    return run_tkinter_script(script)

@router.get("/pick-file")
def pick_file():
    """Opens a native Windows file picker and returns the selected path."""
    try:
        path = _pick_file()
        return {"path": path}
    except Exception as e:
        log.error(f"Erro ao abrir seletor de arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pick-folder")
def pick_folder():
    """Opens a native Windows folder picker and returns the selected path."""
    try:
        path = _pick_folder()
        return {"path": path}
    except Exception as e:
        log.error(f"Erro ao abrir seletor de pasta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
