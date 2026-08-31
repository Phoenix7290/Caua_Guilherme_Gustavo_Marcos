# Customer Support Intent API

TP1 do Projeto de Bloco — Análise e Segurança de Agentes de IA

## Objetivo do projeto

Construir a base de um sistema de atendimento ao cliente com inteligência artificial. Este TP cobre as duas primeiras etapas: a análise exploratória do dataset que vai alimentar o futuro modelo de classificação e a estrutura da API que vai servir esse sistema, já com autenticação JWT funcional. `Ticket Type` e `Ticket Subject` são as variáveis-alvo da classificação de intenção; o modelo de machine learning propriamente dito será implementado em uma etapa futura do bloco — por enquanto, a rota `/predict` retorna uma classificação simulada por regras.

## Dataset

**Customer Support Ticket Dataset** ([Kaggle](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset/data)) — 8.469 chamados de suporte técnico, 17 colunas, incluindo dados do cliente, produto, descrição do problema, tipo/assunto do chamado, prioridade, canal, status e, quando aplicável, tempo de resposta/resolução e satisfação.

A documentação completa (fonte, características, motivo da escolha) e a análise exploratória (inspeção inicial, verificação de qualidade, limpeza, análise univariada e hipóteses sobre a intenção dos usuários) estão em [`eda/eda.ipynb`](eda/eda.ipynb).

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
git clone https://github.com/Phoenix7290/Caua-Guilherme-Gustavo-Marcos.git
cd Caua-Guilherme-Gustavo-Marcos/fastapi

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edite o .env e defina um valor para SECRET_KEY
```

## Execução

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

## Integrantes

- Cauã Henrique
- Guilherme Reis
- Gustavo Gaudereto
- Marcos Ryan
