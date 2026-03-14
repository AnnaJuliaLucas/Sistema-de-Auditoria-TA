# Usar uma imagem Python leve
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências de sistema (psycopg2-binary não precisa, mas se fosse compilar precisaria)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar pastas para persistência (volumes do Railway)
RUN mkdir -p /app/data/evidencias

# Expor a porta 8000
EXPOSE 8000

# Comando para rodar com timeout estendido para uploads pesados
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "600"]
