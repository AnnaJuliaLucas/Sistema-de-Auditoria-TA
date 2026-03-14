import sys
import os
from pathlib import Path

# Vercel-specific path handling
current_dir = Path(__file__).parent.resolve()
root_path = current_dir.parent.resolve()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# Importa o app FastAPI (startup será gerenciado pelo lifespan do FastAPI)
from backend.main import app  # noqa: F401
