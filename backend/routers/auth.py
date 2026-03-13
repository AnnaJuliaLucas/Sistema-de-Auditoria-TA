"""
routers/auth.py — Authentication endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from backend.auth import create_access_token, verify_password, get_password_hash, Token, get_current_user
from backend.db import get_user, create_user
from pydantic import BaseModel
import re

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
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Usuário já cadastrado"
        )
    
    hashed_pass = get_password_hash(body.password)
    create_user(email, hashed_pass)
    return {"ok": True, "message": "Usuário criado com sucesso"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.lower().strip()
    
    user = get_user(email)
    
    # Fallback to default if no users exist at all (bootstrap)
    if not user:
        if not email.endswith("@automateasy.com.br"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito ao domínio @automateasy.com.br"
            )
        
        # If it's the domain but user not found, 
        # and it's the FIRST user ever, we could allow default pass
        # But for now, let's just tell them to register
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado. Por favor, realize o primeiro acesso."
        )

    print(f"DEBUG LOGIN: Email={email}, PassLen={len(form_data.password)}")
    if not verify_password(form_data.password, user["password"]):
        print(f"DEBUG LOGIN: Verify failed for {email}")
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
