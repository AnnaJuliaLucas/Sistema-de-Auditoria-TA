# Sistema de Auditoria TA v2.0

Sistema de auditoria assistida por Inteligência Artificial para análise de conformidade PO.AUT.002.

## Estrutura do Projeto

- `backend/`: API FastAPI (Python 3.10+)
- `frontend/`: Interface Next.js (Node.js 18+)

## Como Executar Localmente

1. Execute o arquivo `Iniciar_Sistema.bat` na raiz do projeto.
2. O sistema instalará automaticamente as dependências e iniciará:
   - Backend: [http://localhost:8000](http://localhost:8000)
   - Frontend: [http://localhost:3000](http://localhost:3000)

## Tecnologias

- **Frontend**: Next.js, React, Tailwind CSS
- **Backend**: FastAPI, SQLite (local), PostgreSQL (produção)
- **IA**: OpenAI, Anthropic, Google Gemini (via API)
