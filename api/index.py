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
    str_e = str(e)
    print("FATAL ERROR during Vercel startup:", file=sys.stderr)
    print(err_msg, file=sys.stderr)
    
    # Criamos um handler ASGI cru (sem FastAPI) para ter certeza absoluta 
    # de que vamos imprimir o erro na tela mesmo se o FastAPI faltar
    import json
    async def app(scope, receive, send):
        assert scope['type'] == 'http'
        body = json.dumps({
            "error": "Backend failed to import on Vercel",
            "exception": str_e,
            "trace": err_msg
        }).encode("utf-8")
        
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [
                [b'content-type', b'application/json'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
