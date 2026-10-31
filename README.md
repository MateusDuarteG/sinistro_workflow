Markdown# 🚗 Insurance Sinistros Workflow (OS)

Sistema backend e frontend de alta fidelidade para gestão e processamento de sinistros de veículos. A aplicação utiliza uma **Máquina de Estados Finita** rígida para garantir a integridade do fluxo de ordens de serviço, complementada por **Controlo de Acessos Baseado em Perfis (RBAC)** e auditoria completa de histórico.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Segurança & Auth:** JWT (JSON Web Tokens), Passlib (Bcrypt), OAuth2
- **Base de Dados:** SQLite (com suporte ORM)
- **Frontend:** HTML5, CSS3 Moderno, JavaScript Vanilla (Fetch API, Dark/Light Theme)
- **Containerização:** Docker, Docker Compose

---

## ⚙️ Arquitetura & Máquina de Estados

O fluxo de estados de um sinistro segue transições estritamente validadas no backend:

[ ABERTO ] ➔ [ EM_PERICIA ] ➔ [ RECUPERAVEL ] ➔ [ AGUARDANDO_PAGAMENTO ] ➔ [ CONCLUIDO ]
↳ [ PERDA_TOTAL ]  ➔ [ AGUARDANDO_PAGAMENTO ] ➔ [ CONCLUIDO ]
### Perfis de Acesso (RBAC):
- **CLIENTE:** Pode abrir novos sinistros e acompanhar o estado dos seus próprios registos.
- **ATENDENTE:** Responsável pela triagem inicial e abertura de ordens de serviço.
- **PERITO:** Insere laudos técnicos, estimativa de danos e avança o estado para perícia.
- **FINANCEIRO:** Aprova pagamentos e conclui os processos elegíveis.

---

## 🚀 Como Executar o Projeto

### Opção 1: Via Docker Compose (Recomendado)

```bash
docker-compose up --build
A API ficará disponível em http://127.0.0.1:8000.Opção 2: Execução Local com PythonInstalar dependências:Bashpip install -r requirements.txt
Iniciar o servidor Backend:Bashuvicorn app.main:app --reload
Aceder à documentação Swagger:
Aceda a http://127.0.0.1:8000/docs para interagir com todos os endpoints.Iniciar o Frontend:
Abra o ficheiro index.html via Live Server ou diretamente no navegador.📌 Principais EndpointsMétodoEndpointDescriçãoPOST/usuarios/Registo de novos utilizadores com perfil definidoPOST/loginAutenticação e geração do token Bearer JWTGET/sinistros/Listagem de sinistros filtrada por perfilPOST/sinistros/Abertura de novos sinistros (suporta anexo/foto)PATCH/sinistros/{id}/statusTransição de estado com validação de regrasGET/sinistros/{id}/historicoTrilha de auditoria completa das alterações
