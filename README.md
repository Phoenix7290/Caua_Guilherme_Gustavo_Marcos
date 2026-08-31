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

A fonte, as principais características e o motivo da escolha do dataset estão detalhados no início do notebook [`eda/eda.ipynb`](eda/eda.ipynb).

## Estrutura de pastas

```
.
├── data/
│   └── customer_support_tickets.csv     # dataset usado no EDA e na API
├── eda/
│   └── eda.ipynb                        # análise exploratória completa
├── fastapi/
│   ├── main.py                          # ponto de entrada da aplicação
│   ├── requirements.txt                 # dependências da API
│   ├── .env.example                     # modelo de variáveis de ambiente
│   ├── models/
│   │   └── schemas.py                   # modelos Pydantic (request/response)
│   ├── routes/
│   │   ├── health.py                    # GET /health
│   │   ├── auth.py                      # POST /auth/token
│   │   └── predict.py                   # POST /predict (protegida)
│   └── security/
│       └── auth.py                      # JWT, OAuth2PasswordBearer, usuário admin
├── others/
│   ├── dfd.png                          # diagrama de fluxo de dados
│   └── dfd.dot                          # fonte do diagrama (Graphviz)
├── .gitignore
└── README.md
```

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/Phoenix7290/Caua-Guilherme-Gustavo-Marcos.git
cd Caua-Guilherme-Gustavo-Marcos/fastapi

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
jupyter notebook eda/eda.ipynb
```

O notebook lê o dataset de `data/customer_support_tickets.csv` por caminho relativo, então execute-o a partir da pasta `eda/`, como o Jupyter já faz por padrão.

### API

A partir do diretório `fastapi/`:

```bash
uvicorn main:app --reload
```

A API sobe em `http://localhost:8000`. A documentação interativa (Swagger) fica em `http://localhost:8000/docs`.

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

A API tem um único usuário, definido em código-fonte (`fastapi/security/auth.py`), com senha armazenada como hash (`bcrypt`):

- **usuário:** `admin`
- **senha:** `admin123`

Fluxo:

1. `POST /auth/token` com `username` e `password` (form-data) → retorna um `access_token` (JWT).
2. Use esse token como `Bearer <token>` no header `Authorization` para acessar rotas protegidas.

## Rotas

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se a API está ativa |
| POST | `/auth/token` | Não | Autentica o usuário admin e retorna um JWT |
| POST | `/predict` | Sim (Bearer JWT) | Recebe o texto de um chamado e retorna uma intenção classificada (regra fixa; modelo de ML será implementado em etapa futura) |

## Segurança

- Autenticação via JWT com `OAuth2PasswordBearer`.
- Senha do usuário admin armazenada com hash `bcrypt` (nunca em texto puro).
- Chave de assinatura do token (`SECRET_KEY`) carregada de variável de ambiente (`.env`, fora do controle de versão) — nunca hardcoded no código-fonte.
- A rota `/predict` exige token JWT válido; tentativas sem token ou com token expirado/inválido retornam `401 Unauthorized`.
- O diagrama de fluxo de dados (`others/dfd.png`) detalha as trust boundaries do sistema (internet pública ↔ borda, borda ↔ dispositivo, rotas públicas ↔ rotas autenticadas) e a análise de confidencialidade, integridade e disponibilidade por componente.

## Hospedagem

A API é hospedada localmente em um Raspberry Pi 5 (Ubuntu Server), exposta publicamente via Cloudflare Tunnel.

## Integrantes da Equipe

- Cauã Henrique
- Guilherme Reis
- Gustavo Gaudereto
- Marcos Ryan
