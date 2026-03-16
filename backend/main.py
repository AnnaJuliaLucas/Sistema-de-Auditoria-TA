"""
main.py — FastAPI application entry point.
Sistema de Auditoria TA — Backend API
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import traceback
import shutil
from datetime import datetime
from pathlib import Path

# Configure logging
RAILWAY_VOL = os.environ.get("RAILWAY_ENVIRONMENT")
log_path = Path("/app/data/app.log") if RAILWAY_VOL else Path("app.log")

try:
    if RAILWAY_VOL:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
except (OSError, PermissionError):
    # Fallback to local file if volume fails
    log_path = Path("app.log")
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
log = logging.getLogger("auditoria_api")
log.info(f"Logging initialized at: {log_path}")

# Railway specific: if we have a volume, use it for temp files to avoid [Errno 28] No space left on device
if os.environ.get("RAILWAY_ENVIRONMENT"):
    volume_tmp = Path("/app/data/tmp")
    volume_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(volume_tmp)
    log.info(f"Using volume for temp files: {volume_tmp}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize database and reclaim space if critical."""
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        try:
            # Truncate log ONLY if it's extremely large (>15MB)
            if os.path.exists(log_path) and os.path.getsize(log_path) > 15 * 1024 * 1024:
                with open(log_path, "w") as f:
                    f.write(f"--- Log Auto-Truncated at {datetime.now().isoformat()} ---\n")
            
            # NOTE: We no longer purge /app/data/uploads here because the disk was increased to 5GB.
            # Persistence is now safe.
        except Exception as e:
            log.error(f"Startup clean error: {e}")
    
    log.info("Starting Sistema de Auditoria TA - Backend API")
    try:
        from pathlib import Path
        ev_file = Path("backend/routers/evidencias.py")
        if ev_file.exists():
            content = ev_file.read_text(errors='replace')
            log.info(f"DEBUG: evidencias.py first 100 chars: {content[:100]}")
            import hashlib
            log.info(f"DEBUG: evidencias.py md5: {hashlib.md5(content.encode()).hexdigest()}")
        else:
            log.info("DEBUG: evidencias.py NOT FOUND locally")
        
        from backend.db import init_db
        init_db()
        log.info("Database initialized")
    except Exception as e:
        log.error(f"DATABASE INITIALIZATION FAILURE: {e}")
    yield
    log.info("Backend stopped")

app = FastAPI(
    title="Sistema de Auditoria TA - Backend API",
    description="API para o Sistema de Auditoria de Automação Industrial",
    version="2.1.5",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Error Handler
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        log.error(f"GLOBAL ERROR: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc), "traceback": traceback.format_exc()}
        )

# Routers
from backend.routers import (
    auditorias, avaliacoes, ia, dashboard, chat, diario, export, 
    evidencias, upload, debug, dados, utils, config, auth, agente
)
app.include_router(auditorias.router)
app.include_router(avaliacoes.router)
app.include_router(ia.router)
app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(diario.router)
app.include_router(export.router)
app.include_router(evidencias.router)
app.include_router(upload.router)
app.include_router(debug.router)
app.include_router(dados.router)
app.include_router(utils.router)
app.include_router(config.router)
app.include_router(auth.router)
app.include_router(agente.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": app.version}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
