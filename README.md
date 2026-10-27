# Sistema de Atendimento ao Cliente com IA

Projeto de Bloco de Análise e Segurança de Agentes de IA

## Objetivo do projeto

Desenvolver um sistema capaz de classificar a intenção de chamados de suporte a partir dos dados enviados pelo cliente. `Ticket Type` e `Ticket Subject` serão as variáveis-alvo da classificação, e o sistema será disponibilizado por uma API FastAPI modular e protegida por autenticação JWT.

## Escopo do projeto

- Análise exploratória: compreensão do problema e do dataset, inspeção inicial, verificação da qualidade, limpeza, preparação e análise univariada.
- Formulação de hipóteses sobre as intenções dos usuários a partir das distribuições observadas.
- API FastAPI modular com as rotas `GET /health`, `POST /auth/token` e `POST /predict`.
- Autenticação JWT com `OAuth2PasswordBearer` e proteção da rota de predição.
- Diagrama de fluxo de dados com entradas, saídas e limites de confiança, acompanhado da análise de confidencialidade, integridade e disponibilidade.

## Dataset

- **Nome:** Customer Support Ticket Dataset
- **Fonte:** [Customer Support Ticket Dataset no Kaggle](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset/data), publicado por `suraj520`
- **Conteúdo:** 8.469 chamados de suporte e 17 colunas com informações sobre clientes, produtos, chamados e atendimento.

A fonte, as principais características e o motivo da escolha do dataset estão detalhados no início do notebook [`eda/eda_tp3.ipynb`](eda/eda_tp3.ipynb).

## Estrutura de pastas

```
.
├── .github/
│   └── workflows/
│       ├── tests.yml                    # CI: execução automatizada da suíte pytest
│       └── zap.yml                      # CI: scan passivo automatizado com OWASP ZAP
├── data/
│   └── customer_support_tickets.csv     # dataset usado no EDA e na API
├── eda/
│   ├── eda_tp3.ipynb                    # notebook com o EDA completo (TP1, TP2 e TP3)
│   └── requirements.txt                 # dependências de data science para o notebook
├── fastapi/
│   ├── main.py                          # ponto de entrada da aplicação
│   ├── database.py                      # engine SQLModel e sessão (get_session)
│   ├── database.db                      # banco SQLite (usuários e predictions)
│   ├── sqlite_database.py               # criação do schema e população inicial (sqlite3)
│   ├── sqlite_populate.py               # script dedicado para popular o banco SQLite
│   ├── limiter.py                       # configuração do SlowAPI (anti brute-force)
│   ├── requirements.txt                 # dependências da API
│   ├── .env.example                     # modelo de variáveis de ambiente
│   ├── Dockerfile                       # imagem da API
│   ├── compose.yml                      # orquestração via Docker Compose
│   ├── models/
│   │   ├── schemas.py                   # modelos Pydantic com extra='forbid'
│   │   └── tables.py                    # tabelas SQLModel (User, Prediction)
│   ├── routes/
│   │   ├── health.py                    # GET /health
│   │   ├── auth.py                      # POST /auth/token (com SlowAPI rate limiter)
│   │   └── predict.py                   # rotas de predição protegidas (com mitigação BOLA)
│   ├── security/
│   │   ├── auth.py                      # JWT, OAuth2PasswordBearer, autenticação via banco
│   │   └── headers.py                   # headers de segurança HTTP e CSP do Swagger UI
│   └── tests/                           # testes automatizados pytest
│       └── test_security.py             # 12 cenários de autenticação, BOLA, rate limit e schema
├── others/
│   ├── dfd.drawio.png                   # diagrama de fluxo de dados
│   ├── dfd.drawio                       # arquivo fonte do diagrama
│   ├── planejamento_tp3.md              # planejamento do modelo ML e pentest adversarial (TP3)
│   └── planejamento.md                  # alias do documento de planejamento
├── tests -> fastapi/tests               # atalho para execução de testes na raiz
├── zap/
│   ├── zap_report.html                  # relatório HTML da auditoria OWASP ZAP
│   ├── zap_report.json                  # relatório JSON estruturado do ZAP
│   └── scan_passivo_zap_TP3.md          # documentação analítica dos findings do ZAP
├── .gitignore
└── README.md
```

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/Phoenix7290/Caua_Guilherme_Gustavo_Marcos.git
cd Caua_Guilherme_Gustavo_Marcos/fastapi

# Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Instalar as dependências
pip install -r requirements.txt

cp .env.example .env
# Edite o .env e defina um valor para SECRET_KEY
```

## Execução

### EDA (notebook)

Abra o notebook no Jupyter ou no VS Code e execute as células em ordem:

```bash
jupyter notebook eda/eda_tp3.ipynb
```

O notebook lê o dataset de `data/customer_support_tickets.csv` por caminho relativo, então execute-o a partir da pasta `eda/`, como o Jupyter já faz por padrão.

### Banco de Dados SQLite (Criação e População)

A partir do diretório `fastapi/`:

```bash
# 1. Criação do schema e população inicial (recria database.db)
python sqlite_database.py

# 2. População dedicada do banco de dados (reinserção determinística)
python sqlite_populate.py
```

### Execução dos Testes Automatizados (pytest)

A suíte de testes de segurança cobre autenticação válida/inválida, prevenção a BOLA (404), validação estrita com `extra='forbid'`, bloqueio por rate limiting (429) e integridade de rotas protegidas.

```bash
# Execução a partir da raiz do repositório:
pytest tests/ -v

# Ou a partir da pasta fastapi/:
cd fastapi
pytest tests/ -v
```

### Auditoria de Segurança com OWASP ZAP

A API foi auditada via scan passivo com o contêiner oficial do OWASP ZAP:

```bash
# Com a API rodando em http://localhost:8000:
docker run --rm --network host \
  -v "$PWD/zap:/zap/wrk:rw" \
  zaproxy/zap-stable:latest zap-api-scan.py \
  -t http://localhost:8000/openapi.json -f openapi \
  -S -I -r zap_report.html -J zap_report.json
```

O relatório consolidado com **zero findings Medium ou High** e a análise detalhada de mitigações estão disponíveis em [`zap/scan_passivo_zap_TP3.md`](zap/scan_passivo_zap_TP3.md).

### Planejamento da Próxima Etapa (TP4/TP5)

O documento de transição contendo o modelo candidato (Regressão Logística), técnica de vetorização (`CountVectorizer`) e os alvos autorizados para testes de invasão e pentest adversarial está formalizado em [`others/planejamento_tp3.md`](others/planejamento_tp3.md).

### API

A partir do diretório `fastapi/`:

```bash
uvicorn main:app --reload
```

A API sobe em `http://localhost:8000`. A documentação interativa (Swagger) fica em `http://localhost:8000/docs`.

## Ambiente publicado

A API também está disponível publicamente (hospedada em um Raspberry Pi 5, exposta via Cloudflare Tunnel):

**URL base:** https://supportdesk-api.marcosryan.com

Documentação interativa (Swagger): https://supportdesk-api.marcosryan.com/docs

### Testando

```bash
# 1. Health check e inspeção de Headers de Segurança HTTP
curl -I https://supportdesk-api.marcosryan.com/health

# 2. Teste de CORS com preflight (origem autorizada na allowlist)
curl -I -X OPTIONS https://supportdesk-api.marcosryan.com/predict \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# 3. Autenticação (usuários de exemplo: admin / admin123 e alice / alice123)
curl -X POST https://supportdesk-api.marcosryan.com/auth/token \
  -d "username=admin&password=admin123"

# 4. Criar predição (substitua <TOKEN_ADMIN> pelo access_token retornado acima)
curl -X POST https://supportdesk-api.marcosryan.com/predict \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -H "Content-Type: application/json" \
  -d '{"text": "meu produto parou de funcionar"}'

# 5. Listar predições do usuário autenticado (retorna apenas as predições do admin)
curl https://supportdesk-api.marcosryan.com/predict \
  -H "Authorization: Bearer <TOKEN_ADMIN>"

# 6. Teste de BOLA (Broken Object Level Authorization):
# Obtenha o token da Alice e tente acessar uma predição pertencente ao Admin (ex: id 1):
curl -X POST https://supportdesk-api.marcosryan.com/auth/token \
  -d "username=alice&password=alice123"

# A requisição abaixo retorna 404 Not Found (BOLA mitigado):
curl https://supportdesk-api.marcosryan.com/predict/1 \
  -H "Authorization: Bearer <TOKEN_ALICE>"

# 7. Teste de validação de schema (extra='forbid'):
# Envio de atributo extra não previsto retorna 422 Unprocessable Entity:
curl -X POST https://supportdesk-api.marcosryan.com/predict \
  -H "Authorization: Bearer <TOKEN_ALICE>" \
  -H "Content-Type: application/json" \
  -d '{"text": "quero reembolso", "campo_invalido": 123}'
```

## Self Hosting

Requer Docker e Docker Compose instalados.

A partir do diretório `fastapi/`:

```bash
cp .env.example .env
# edite o .env e defina o SECRET_KEY

docker compose up -d --build
```

A API sobe em `http://localhost:8000`.

## Autenticação

Os usuários ficam na tabela `user` do SQLite (`fastapi/database.db`), com senha armazenada como hash (`bcrypt`). O banco é criado e populado por `fastapi/sqlite_database.py` (`python sqlite_database.py`, a partir de `fastapi/`; recria o arquivo do zero) com dois usuários:

| usuário | senha |
|---|---|
| `admin` | `admin123` |
| `alice` | `alice123` |

Cada predição salva na tabela `prediction` possui um `owner_id` (chave estrangeira para `user.id`). Todas as consultas da API usam SQLModel, sem SQL raw.

Fluxo:

1. `POST /auth/token` com `username` e `password` (form-data) → retorna um `access_token` (JWT).
2. Use esse token como `Bearer <token>` no header `Authorization` para acessar rotas protegidas.

## Rotas

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se a API está ativa |
| POST | `/auth/token` | Não | Autentica um usuário do banco e retorna um JWT |
| POST | `/predict` | Sim (Bearer JWT) | Recebe o texto de um chamado e retorna uma intenção classificada (regra fixa; modelo de ML será implementado em etapa futura) e salva a predição para o usuário autenticado |
| GET | `/predict` | Sim (Bearer JWT) | Lista somente as predições do usuário autenticado |
| GET | `/predict/{id}` | Sim (Bearer JWT) | Retorna uma predição do usuário autenticado (`404` se não existir ou pertencer a outro usuário) |

## Segurança

- **Autenticação via JWT com OAuth2PasswordBearer**: tokens assinados com algoritmo HS256 e expiração configurada.
- **Armazenamento Seguro de Credenciais**: senhas dos usuários armazenadas exclusivamente como hash `bcrypt` (nunca em texto puro).
- **Chave Secreta Protegida**: `SECRET_KEY` carregada via variáveis de ambiente (`.env`), sem exposição no código-fonte.
- **Controle de Acesso por Ownership (Mitigação de BOLA / IDOR - OWASP API Top 10)**:
  - Cada predição é associada ao `owner_id` (chave estrangeira para `user.id`).
  - `GET /predict` retorna unicamente as predições de posse do usuário logado.
  - `GET /predict/{id}` valida se o recurso pertence ao solicitante. Se pertencer a outro usuário ou não existir, retorna `404 Not Found` (evitando Broken Object Level Authorization e enumeração maliciosa de IDs).
- **Validação Estrita de Schemas (`extra='forbid'`)**:
  - `PredictRequest` configurado com `extra="forbid"` via Pydantic V2. Requisições contendo atributos adicionais não previstos são rejeitadas com status `422 Unprocessable Entity`.
- **Headers HTTP de Segurança (OWASP Top 10)** via middleware FastAPI (`SecurityHeadersMiddleware`):
  - `Strict-Transport-Security` (HSTS): `max-age=31536000; includeSubDomains` para impor uso de HTTPS.
  - `X-Frame-Options`: `DENY` para mitigar ataques de Clickjacking.
  - `X-Content-Type-Options`: `nosniff` impedindo MIME-type sniffing no navegador.
  - `Content-Security-Policy` (CSP): restringe carregamento de recursos externos às origens estritas necessárias (com suporte aos assets do Swagger UI via CDN).
  - Headers complementares: `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin` e `Permissions-Policy`.
- **CORS com Allowlist Explícita**:
  - Configurado via `CORSMiddleware` sem uso de wildcard (`*`).
  - Origens explicitamente permitidas por padrão (`http://localhost`, `http://localhost:8000`, `http://localhost:3000`, `https://supportdesk-api.marcosryan.com`), customizáveis via variável `ALLOWED_ORIGINS` no `.env`.
- **Diagrama de Fluxo de Dados**: localizado em `others/dfd.drawio.png`, mapeia trust boundaries (internet pública ↔ borda, borda ↔ host local, rotas públicas ↔ rotas autenticadas) e analisa controles de CIA (Confidencialidade, Integridade e Disponibilidade).

## Hospedagem

A API é hospedada localmente em um Raspberry Pi 5 (Ubuntu Server), exposta publicamente via Cloudflare Tunnel.

## Integrantes da Equipe

- Cauã Henrique
- Guilherme Reis
- Gustavo Gaudereto
- Marcos Ryan
