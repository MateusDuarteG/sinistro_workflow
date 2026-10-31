import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RoleEnum(str, enum.Enum):
    ATENDENTE = "atendente"
    PERITO = "perito"
    FINANCEIRO = "financeiro"
    CLIENTE = "cliente"

class StatusSinistroEnum(str, enum.Enum):
    ABERTO = "ABERTO"                   # Criado pelo cliente ou atendente
    EM_PERICIA = "EM_PERICIA"           # Encaminhado para avaliação técnica
    RECUPERAVEL = "RECUPERAVEL"         # Perito indicou reparo em oficina
    PERDA_TOTAL = "PERDA_TOTAL"         # Perito indicou indenização (PT)
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO" # Encaminhado ao Financeiro
    CONCLUIDO = "CONCLUIDO"             # Reembolso feito / Carro arrumado
    CANCELADO = "CANCELADO"             # Fraude ou desistência

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(Enum(RoleEnum), default=RoleEnum.CLIENTE, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

class Sinistro(Base):
    __tablename__ = "sinistros"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String, unique=True, index=True)
    placa_veiculo = Column(String)
    modelo_veiculo = Column(String)
    descricao_dano = Column(String)
    status = Column(Enum(StatusSinistroEnum), default=StatusSinistroEnum.ABERTO)
    valor_estimado = Column(Float, nullable=True)
    laudo_perito = Column(String, nullable=True)
    foto_veiculo = Column(String, nullable=True) # <-- Novo campo para a foto do dano
    cliente_id = Column(Integer, ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)

    cliente = relationship("Usuario", foreign_keys=[cliente_id])
    historicos = relationship("HistoricoStatus", back_populates="sinistro", cascade="all, delete-orphan")

class HistoricoStatus(Base):
    __tablename__ = "historico_status"

    id = Column(Integer, primary_key=True, index=True)
    sinistro_id = Column(Integer, ForeignKey("sinistros.id"), nullable=False)
    status_anterior = Column(String(50), nullable=False)
    status_novo = Column(String(50), nullable=False)
    observacao = Column(Text, nullable=True)
    alterado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    sinistro = relationship("Sinistro", back_populates="historicos")