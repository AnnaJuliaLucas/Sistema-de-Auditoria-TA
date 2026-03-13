import sys
from pathlib import Path

# Adiciona o diretório atual ao path para importar database
sys.path.append(str(Path.cwd()))

import database

def run_init():
    print("Iniciando migração do banco de dados...")
    try:
        database.init_db()
        print("SUCCESS: Banco de dados inicializado/migrado com sucesso.")
    except Exception as e:
        print(f"ERROR: Falha ao inicializar banco: {e}")

if __name__ == "__main__":
    run_init()
