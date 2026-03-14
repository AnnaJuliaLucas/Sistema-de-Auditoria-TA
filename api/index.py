import sys
import os
from pathlib import Path

# Vercel-specific path handling
current_dir = Path(__file__).parent.resolve()
root_path = current_dir.parent.resolve()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

try:
    from backend.main import app  # noqa: F401
except Exception as e:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def catch_all(request, path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to import application",
                "message": str(e),
                "traceback": traceback.format_exc()
            }
        )
