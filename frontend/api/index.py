import sys
from os.path import dirname, join, realpath

# Adiciona o diretório backend ao path (subindo 3 níveis: api -> frontend -> raiz)
backend_path = join(dirname(dirname(dirname(realpath(__file__)))), "backend")
sys.path.append(backend_path)

from backend.main import app

# Ponto de entrada para o runtime Python do Vercel
handler = app
