import sys
import os
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para encontrar o módulo 'backend'
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from backend.main import app

# Vercel espera uma variável chamada 'app'
# Se o FastAPI estiver em backend.main:app, já está correto.
