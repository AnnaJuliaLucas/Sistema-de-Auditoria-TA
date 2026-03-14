"""
main.py — FastAPI application entry point.
Sistema de Auditoria TA — Backend API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auditoria_api")

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize database."""
    log.info("🚀 Iniciando Sistema de Auditoria TA — Backend API")
    try:
        from backend.db import init_db
        init_db()
        log.info("✅ Banco de dados inicializado")
    except Exception as e:
        log.error(f"❌ FALHA NA INICIALIZAÇÃO DO BANCO: {e}")
        # We don't reraise to allow the app to boot and show errors on health check/routes
    yield
    log.info("🛑 Backend encerrado")


app = FastAPI(
    title="Sistema de Auditoria TA",
    description="API para o Sistema de Auditoria de Automação Industrial",
    version="2.0.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_trace = traceback.format_exc()
    log.error(f"GLOBAL ERROR: {err_trace}")
    # Return more detail during debugging phase
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": err_trace
        }
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin")
    log.info(f"Incoming request: {request.method} {request.url} from origin: {origin}")
    response = await call_next(request)
    return response

# Register routers
from backend.routers.auditorias import router as auditorias_router
from backend.routers.avaliacoes import router as avaliacoes_router
from backend.routers.ia import router as ia_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.chat import router as chat_router
from backend.routers.diario import router as diario_router
from backend.routers.export import router as export_router
from backend.routers.evidencias import router as evidencias_router
from backend.routers.dados import router as dados_router
from backend.routers.utils import router as utils_router
from backend.routers.config import router as config_router
from backend.routers.auth import router as auth_router
from backend.routers.debug import router as debug_router

app.include_router(debug_router)
app.include_router(auth_router)
app.include_router(auditorias_router)
app.include_router(avaliacoes_router)
app.include_router(ia_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(diario_router)
app.include_router(export_router)
app.include_router(evidencias_router)
app.include_router(dados_router)
app.include_router(utils_router)
app.include_router(config_router)

# CORS — MASSIVE SIMPLIFICATION FOR DEBUGGING
# We allow everything to confirm if CORS is truly the culprit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Must be False for "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
