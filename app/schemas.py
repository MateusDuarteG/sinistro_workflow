from pydantic import BaseModel, EmailStr
from typing import Optional, Any
from datetime import datetime
from app.models import RoleEnum, StatusSinistroEnum

# --- USUÁRIOS & AUTH ---
class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: RoleEnum = RoleEnum.CLIENTE

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil: RoleEnum

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# --- SINISTROS / OS ---
class SinistroCreate(BaseModel):
    placa_veiculo: str
    modelo_veiculo: str
    descricao_dano: str
    cliente_id: int

class SinistroUpdateStatus(BaseModel):
    novo_status: StatusSinistroEnum
    observacao: Optional[str] = None
    valor_estimado: Optional[float] = None
    laudo_perito: Optional[str] = None

class HistoricoResponse(BaseModel):
    id: int
    status_anterior: str
    status_novo: str
    observacao: Optional[str]
    alterado_por_id: int
    criado_em: datetime | str

    class Config:
        from_attributes = True

class SinistroResponse(BaseModel):
    id: int
    protocolo: str
    placa_veiculo: str
    modelo_veiculo: str
    descricao_dano: str
    status: str
    valor_estimado: Optional[float] = None
    foto_veiculo: Optional[str] = None  # <-- Certifica-te de que esta linha existe aqui!
    cliente_id: int

    class Config:
        from_attributes = True