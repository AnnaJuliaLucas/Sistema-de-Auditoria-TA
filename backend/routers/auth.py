"""
routers/auth.py — Authentication endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from backend.auth import create_access_token, verify_password, get_password_hash, Token, get_current_user
from backend.db import get_user, create_user, get_db
from pydantic import BaseModel
import re
import logging

log = logging.getLogger("auditoria_auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Senha deve conter ao menos uma letra maiúscula")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Senha deve conter ao menos uma letra minúscula")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Senha deve conter ao menos um número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Senha deve conter ao menos um caractere especial")


@router.post("/register")
async def register(body: RegisterRequest):
    email = body.email.lower().strip()
    if not email.endswith("@automateasy.com.br"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao domínio @automateasy.com.br"
        )
    
    validate_password(body.password)
    
    existing = get_user(email)
    hashed_pass = get_password_hash(body.password)
    
    if existing:
        # Update password for existing user (acts as password reset)
        with get_db() as conn:
            conn.execute("UPDATE users SET password=? WHERE email=?", (hashed_pass, email))
            conn.commit()
        log.info(f"Password updated for {email}")
        return {"ok": True, "message": "Senha atualizada com sucesso! Agora você pode entrar."}
    
    create_user(email, hashed_pass)
    log.info(f"New user registered: {email}")
    return {"ok": True, "message": "Usuário criado com sucesso! Agora você pode entrar."}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.lower().strip()
    
    user = get_user(email)
    
    if not user:
        if not email.endswith("@automateasy.com.br"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito ao domínio @automateasy.com.br"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado. Por favor, configure seu primeiro acesso."
        )

    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": email})
    return {"access_token": access_token, "token_type": "bearer", "email": email}


@router.get("/me")
async def get_me(current_user: str = Depends(get_current_user)):
    return {"email": current_user}


@router.post("/cleanup-users")
async def cleanup_users():
    """Remove all old hardcoded users, keep only teste@automateasy.com.br."""
    try:
        with get_db() as conn:
            for old_email in ["admin@automateasy.com.br", "anna@automateasy.com.br", "duda@automateasy.com.br"]:
                conn.execute("DELETE FROM users WHERE email=?", (old_email,))
            conn.commit()
            
            rows = conn.execute("SELECT email, role FROM users").fetchall()
            users = [{"email": r["email"], "role": r["role"]} for r in rows]
        
        return {"ok": True, "message": "Usuários antigos removidos", "remaining_users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
