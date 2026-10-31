from fastapi import HTTPException, status
from app.models import StatusSinistroEnum, RoleEnum

# Dicionário de transições permitidas (State Machine Matrix)
TRANSICOES_PERMITIDAS = {
    StatusSinistroEnum.ABERTO: [
        StatusSinistroEnum.EM_PERICIA,
        StatusSinistroEnum.CANCELADO
    ],
    StatusSinistroEnum.EM_PERICIA: [
        StatusSinistroEnum.RECUPERAVEL,
        StatusSinistroEnum.PERDA_TOTAL,
        StatusSinistroEnum.CANCELADO
    ],
    StatusSinistroEnum.RECUPERAVEL: [
        StatusSinistroEnum.CONCLUIDO,
        StatusSinistroEnum.CANCELADO
    ],
    StatusSinistroEnum.PERDA_TOTAL: [
        StatusSinistroEnum.AGUARDANDO_PAGAMENTO,
        StatusSinistroEnum.CANCELADO
    ],
    StatusSinistroEnum.AGUARDANDO_PAGAMENTO: [
        StatusSinistroEnum.CONCLUIDO
    ],
    StatusSinistroEnum.CONCLUIDO: [],
    StatusSinistroEnum.CANCELADO: []
}

# Permissões por cargo para cada transição de status
PERMISSOES_POR_STATUS = {
    StatusSinistroEnum.EM_PERICIA: [RoleEnum.ATENDENTE, RoleEnum.PERITO],
    StatusSinistroEnum.RECUPERAVEL: [RoleEnum.PERITO],
    StatusSinistroEnum.PERDA_TOTAL: [RoleEnum.PERITO],
    StatusSinistroEnum.AGUARDANDO_PAGAMENTO: [RoleEnum.PERITO, RoleEnum.FINANCEIRO],
    StatusSinistroEnum.CONCLUIDO: [RoleEnum.FINANCEIRO, RoleEnum.ATENDENTE],
    StatusSinistroEnum.CANCELADO: [RoleEnum.ATENDENTE, RoleEnum.FINANCEIRO]
}

def validar_transicao_estado(status_atual: StatusSinistroEnum, novo_status: StatusSinistroEnum, user_role: RoleEnum):
    # 1. Verifica se a transição física é permitida pela matriz
    if novo_status not in TRANSICOES_PERMITIDAS.get(status_atual, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transição inválida: Não é permitido passar de '{status_atual}' para '{novo_status}'."
        )
    
    # 2. Verifica se o cargo do utilizador tem permissão para realizar esta mudança
    perfis_autorizados = PERMISSOES_POR_STATUS.get(novo_status, [])
    if user_role not in perfis_autorizados and user_role != RoleEnum.ATENDENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: O seu perfil ('{user_role}') não tem permissão para mover um sinistro para o estado '{novo_status}'."
        )
    
    return True