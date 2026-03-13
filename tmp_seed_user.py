import sys
from pathlib import Path
from passlib.context import CryptContext

# Adiciona o diretório atual ao path para importar backend.db
sys.path.append(str(Path.cwd()))

from backend.db import create_user, get_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_admin():
    email = "admin@automateasy.com.br"
    password = "Admin@1234!"
    
    print(f"Verificando se o usuário {email} já existe...")
    user = get_user(email)
    
    if user:
        print(f"INFO: Usuário {email} já existe.")
    else:
        print(f"Criando usuário {email}...")
        hashed_pw = pwd_context.hash(password)
        create_user(email, hashed_pw, role="admin")
        print(f"SUCCESS: Usuário {email} criado com sucesso.")
        print(f"Senha: {password}")

if __name__ == "__main__":
    seed_admin()
