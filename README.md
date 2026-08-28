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
├── README.md            # Este arquivo
├── requirements.txt     # Dependências do projeto
├── data/
│   └── customer_support_tickets.csv   # Dataset base
├── eda/
│   └── eda.ipynb        # Análise exploratória de dados
├── fastapi/
│   └── main.py          # API FastAPI
└── others/
    └── dfd.md           # Diagrama de fluxo de dados
```

## Instalação

Requisitos: Python 3.11 ou superior.

```bash
# Clonar o repositório
git clone https://github.com/Phoenix7290/Caua-Guilherme-Gustavo-Marcos.git
cd Caua-Guilherme-Gustavo-Marcos

# Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Instalar as dependências
pip install -r requirements.txt
```

## Execução

### EDA (notebook)

Abra o notebook no Jupyter ou no VS Code e execute as células em ordem:

```bash
jupyter notebook eda/eda.ipynb
```

O notebook lê o dataset de `data/customer_support_tickets.csv` por caminho relativo, então execute-o a partir da pasta `eda/`, como o Jupyter já faz por padrão.

### API

```bash
cd fastapi
uvicorn main:app --reload
```

A documentação interativa fica disponível em `http://localhost:8000/docs`.

## Equipe

Cauã, Guilherme, Gustavo e Marcos.
