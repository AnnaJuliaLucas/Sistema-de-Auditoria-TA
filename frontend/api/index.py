import sys
from os.path import dirname, join, realpath

# O diretório raiz agora é o diretório atual (frontend)
# api/index.py -> api/../ -> frontend/
root_path = dirname(dirname(realpath(__file__)))
sys.path.append(root_path)

# Adiciona explicitamente o diretório backend ao path
backend_path = join(root_path, "backend")
sys.path.append(backend_path)

from backend.main import app

# Ponto de entrada para o runtime Python do Vercel
handler = app
