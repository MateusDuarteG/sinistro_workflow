from datetime import datetime, timedelta
from typing import List, Optional
import shutil
import os

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base, get_db
from app.models import Usuario, Sinistro, HistoricoStatus, RoleEnum, StatusSinistroEnum
from app.schemas import (
    UsuarioCreate, UsuarioResponse, Token, 
    SinistroCreate, SinistroResponse, SinistroUpdateStatus,
    HistoricoResponse
)
from app.state_machine import validar_transicao_estado

# Cria a pasta de uploads se não existir
UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Cria as tabelas na base de dados automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Gestão de Sinistros - Workflow OS",
    version="1.0.0",
    description="API orientada a estados para gestão de sinistros de seguradoras."
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações de Segurança (JWT & Hashing de Senhas)
SECRET_KEY = "sua-chave-secreta-super-segura-muda-depois"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def verificar_senha(senha_plana, senha_hash):
    return pwd_context.verify(senha_plana, senha_hash)

def criar_hash_senha(senha):
    return pwd_context.hash(senha)

def criar_token_acesso(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependência para obter o utilizador autenticado atual através do Token JWT
def obter_utilizador_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais de autenticação inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- ROTAS DE AUTENTICAÇÃO E UTILIZADORES ---

@app.post("/usuarios/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_utilizador(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registado no sistema.")
    
    hashed_password = criar_hash_senha(usuario.senha)
    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=hashed_password,
        perfil=usuario.perfil
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario

@app.post("/login", response_model=Token)
def login_para_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not user or not verificar_senha(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_token_acesso(
        data={"sub": user.email, "perfil": user.perfil.value}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/perfil/me", response_model=UsuarioResponse)
def ler_perfil_atual(current_user: Usuario = Depends(obter_utilizador_atual)):
    return current_user

# --- ROTAS DE SINISTROS (WORKFLOW OS) ---

@app.post("/sinistros/", response_model=SinistroResponse, status_code=status.HTTP_201_CREATED)
def abrir_sinistro(
    placa_veiculo: str = Form(...),
    modelo_veiculo: str = Form(...),
    descricao_dano: str = Form(...),
    cliente_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(obter_utilizador_atual)
):
    # Apenas Atendentes ou Clientes podem abrir um sinistro
    if current_user.perfil not in [RoleEnum.ATENDENTE, RoleEnum.CLIENTE]:
        raise HTTPException(status_code=403, detail="Não tem permissão para abrir um sinistro.")
    
    foto_path = None
    if file:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)
        foto_path = file_location

    # Gera um número de protocolo único baseado no timestamp
    protocolo_gerado = f"SIN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    novo_sinistro = Sinistro(
        protocolo=protocolo_gerado,
        placa_veiculo=placa_veiculo.upper(),
        modelo_veiculo=modelo_veiculo,
        descricao_dano=descricao_dano,
        status=StatusSinistroEnum.ABERTO,
        cliente_id=cliente_id,
        foto_veiculo=foto_path
    )
    db.add(novo_sinistro)
    db.commit()
    db.refresh(novo_sinistro)
    
    # Regista histórico inicial
    historico = HistoricoStatus(
        sinistro_id=novo_sinistro.id,
        status_anterior="CRIACAO",
        status_novo=StatusSinistroEnum.ABERTO.value,
        observacao="Sinistro aberto no sistema.",
        alterado_por_id=current_user.id
    )
    db.add(historico)
    db.commit()
    
    return novo_sinistro

@app.get("/sinistros/", response_model=List[SinistroResponse])
def listar_sinistros(db: Session = Depends(get_db), current_user: Usuario = Depends(obter_utilizador_atual)):
    query = db.query(Sinistro)
    
    if current_user.perfil == RoleEnum.CLIENTE:
        return query.filter(Sinistro.cliente_id == current_user.id).all()
    elif current_user.perfil == RoleEnum.PERITO:
        return query.filter(Sinistro.status.in_([StatusSinistroEnum.ABERTO, StatusSinistroEnum.EM_PERICIA])).all()
    elif current_user.perfil == RoleEnum.FINANCEIRO:
        return query.filter(Sinistro.status.in_([StatusSinistroEnum.PERDA_TOTAL, StatusSinistroEnum.AGUARDANDO_PAGAMENTO, StatusSinistroEnum.CONCLUIDO])).all()
    
    return query.all()
# --- ROTA PÚBLICA PARA O PORTAL DO CLIENTE (MOBILE / SMS) ---
@app.post("/cliente/sinistros/", response_model=SinistroResponse, status_code=status.HTTP_201_CREATED)
def abrir_sinistro_cliente_externo(
    placa_veiculo: str = Form(...),
    modelo_veiculo: str = Form(...),
    descricao_dano: str = Form(...),
    cliente_id: int = Form(1),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    foto_path = None
    if file and file.filename:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)
        foto_path = file_location  # Salva o caminho do ficheiro

    protocolo_gerado = f"SIN-EXT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    novo_sinistro = Sinistro(
        protocolo=protocolo_gerado,
        placa_veiculo=placa_veiculo.upper(),
        modelo_veiculo=modelo_veiculo,
        descricao_dano=descricao_dano,
        status=StatusSinistroEnum.ABERTO,
        cliente_id=cliente_id,
        foto_veiculo=foto_path
    )
    db.add(novo_sinistro)
    db.commit()
    db.refresh(novo_sinistro)
    
    # --- REGISTA O HISTÓRICO INICIAL OBRIGATÓRIO PARA APARECER NO MODAL ---
    historico = HistoricoStatus(
        sinistro_id=novo_sinistro.id,
        status_anterior="CRIACAO_EXTERNA",
        status_novo=StatusSinistroEnum.ABERTO.value,
        observacao="Sinistro aberto via Portal Mobile do Segurado (SMS/Link).",
        alterado_por_id=cliente_id
    )
    db.add(historico)
    db.commit()
    
    return novo_sinistro

@app.get("/sinistros/{sinistro_id}/historico", response_model=List[HistoricoResponse])
def obter_historico_sinistro(
    sinistro_id: int, 
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(obter_utilizador_atual)
):
    sinistro = db.query(Sinistro).filter(Sinistro.id == sinistro_id).first()
    if not sinistro:
        raise HTTPException(status_code=404, detail="Sinistro não encontrado.")
    
    if current_user.perfil == RoleEnum.CLIENTE and sinistro.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a este sinistro.")
    
    historicos = db.query(HistoricoStatus).filter(HistoricoStatus.sinistro_id == sinistro_id).all()
    return historicos

@app.patch("/sinistros/{sinistro_id}/status", response_model=SinistroResponse)
def atualizar_status_sinistro(
    sinistro_id: int, 
    dados_atualizacao: SinistroUpdateStatus, 
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(obter_utilizador_atual)
):
    sinistro = db.query(Sinistro).filter(Sinistro.id == sinistro_id).first()
    if not sinistro:
        raise HTTPException(status_code=404, detail="Sinistro não encontrado.")
    
    status_antigo = sinistro.status
    novo_status = dados_atualizacao.novo_status
    
    validar_transicao_estado(status_antigo, novo_status, current_user.perfil)
    
    if dados_atualizacao.valor_estimado is not None:
        sinistro.valor_estimado = dados_atualizacao.valor_estimado
    if dados_atualizacao.laudo_perito is not None:
        sinistro.laudo_perito = dados_atualizacao.laudo_perito
        
    sinistro.status = novo_status
    db.commit()
    
    historico = HistoricoStatus(
        sinistro_id=sinistro.id,
        status_anterior=status_antigo.value,
        status_novo=novo_status.value,
        observacao=dados_atualizacao.observacao,
        alterado_por_id=current_user.id
    )
    db.add(historico)
    db.commit()
    db.refresh(sinistro)
    
    return sinistro