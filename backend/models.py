"""
models.py — Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ─── Auditoria ────────────────────────────────────────────────────────────────

class AuditoriaOut(BaseModel):
    id: int
    unidade: str
    area: str
    ciclo: str
    status: str = "em_andamento"
    data_criacao: Optional[str] = None
    data_atualizacao: Optional[str] = None
    assessment_file_path: Optional[str] = None
    evidence_folder_path: Optional[str] = None
    observacoes: Optional[str] = None
    total_subitens: int = 0
    subitens_avaliados: int = 0
    media_nota_final: Optional[float] = None
    ia_analisados: int = 0
    modo_analise: str = "completo"


class AuditoriaConfig(BaseModel):
    assessment_file_path: str = ""
    evidence_folder_path: str = ""
    openai_api_key: str = ""
    ai_provider: str = "openai"
    ai_base_url: Optional[str] = None
    observacoes: Optional[str] = None
    modo_analise: str = "completo"


class StatusUpdate(BaseModel):
    status: str


# ─── Avaliação ────────────────────────────────────────────────────────────────

class AvaliacaoOut(BaseModel):
    id: int
    auditoria_id: int
    pratica_num: Optional[int] = None
    pratica_nome: Optional[str] = None
    subitem_idx: Optional[int] = None
    subitem_nome: Optional[str] = None
    evidencia_descricao: Optional[str] = None
    nivel_0: Optional[str] = None
    nivel_1: Optional[str] = None
    nivel_2: Optional[str] = None
    nivel_3: Optional[str] = None
    nivel_4: Optional[str] = None
    nota_self_assessment: Optional[int] = None
    decisao: str = "pendente"
    nota_final: Optional[int] = None
    descricao_nc: Optional[str] = None
    comentarios: Optional[str] = None
    ia_decisao: Optional[str] = None
    ia_nota_sugerida: Optional[int] = None
    ia_confianca: Optional[str] = None
    ia_pontos_atendidos: Optional[str] = None
    ia_pontos_faltantes: Optional[str] = None
    ia_analise_detalhada: Optional[str] = None
    ia_status: Optional[str] = None


class DecisaoUpdate(BaseModel):
    decisao: str = Field(..., pattern="^(permanece|insuficiente|inexistente|pendente)$")
    nota_final: Optional[int] = Field(None, ge=0, le=4)
    descricao_nc: str = ""
    comentarios: str = ""


class NotaPreview(BaseModel):
    decisao: str
    nota_sa: int
    nota_livre: Optional[int] = None


# ─── IA ───────────────────────────────────────────────────────────────────────

class IAAnalyzeRequest(BaseModel):
    api_key: str = ""
    economico: bool = False
    modo_analise: Optional[str] = None
    provider: str = "openai"
    base_url: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class IAChatRequest(BaseModel):
    api_key: str = ""
    message: str
    economico: bool = False
    provider: str = "openai"
    base_url: Optional[str] = None


# ─── Estatísticas ─────────────────────────────────────────────────────────────

class EstatisticasOut(BaseModel):
    total: int = 0
    avaliados: int = 0
    ia_ok: int = 0
    media_final: Optional[float] = None
    media_sa: Optional[float] = None
