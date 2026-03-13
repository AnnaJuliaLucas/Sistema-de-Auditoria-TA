import sys
import os
from pathlib import Path

# Vercel-specific path handling
current_dir = Path(__file__).parent.resolve()
root_path = current_dir.parent.resolve()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

try:
    # Importa o app FastAPI (startup será gerenciado pelo lifespan do FastAPI)
    from backend.main import app  # noqa: F401
    
    # Adicionando uma rota de diagnóstico forçada para sabermos que o App montou
    @app.get("/api/vercel-debug")
    def get_vercel_debug():
        import sys, os
        return {
            "status": "Online",
            "python": sys.version,
            "cwd": os.getcwd()
        }
except Exception as e:
    import traceback
    err_msg = traceback.format_exc()
    print("FATAL ERROR during Vercel startup:", file=sys.stderr)
    print(err_msg, file=sys.stderr)
    
    # Em Vercel, se o import falhar, criamos um App falso que só devolve o erro
    # Assim paramos o Crash 500 silencioso e vemos o erro na tela
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend failed to import on Vercel",
                "exception": str(e),
                "traceback": err_msg
            }
        )
