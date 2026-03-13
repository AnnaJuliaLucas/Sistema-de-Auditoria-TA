@echo off
title Sistema de Auditoria TA v2.0
echo ============================================
echo   Sistema de Auditoria TA v2.0
echo   Next.js + FastAPI
echo ============================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado! Instale Python 3.10+
    pause
    exit /b 1
)

:: Check if Node is available
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado! Instale Node.js 18+
    pause
    exit /b 1
)

:: Install backend dependencies if needed
echo [1/4] Verificando dependencias do backend...
pip install -q -r backend\requirements.txt

:: Install frontend dependencies if needed
echo [2/4] Verificando dependencias do frontend...
if not exist frontend\node_modules (
    cd frontend
    npm install
    cd ..
)

:: Start backend (FastAPI) in background
echo [3/4] Iniciando backend FastAPI na porta 8000...
start "Backend FastAPI" cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to be ready
timeout /t 3 /nobreak >nul

:: Start frontend (Next.js)
echo [4/4] Iniciando frontend Next.js na porta 3000...
echo.
echo ============================================
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Abrindo navegador...
start http://localhost:3000

cd frontend
npm run dev
