# Agente Autônomo SupportDesk (TP4 — Item 4)

Agente de atendimento ao cliente implementado com **OpenAI Agents SDK** (`Agent`, `Runner.run`, `@function_tool`) integrado ao modelo **Groq (`openai/gpt-oss-20b`)** e à rota protegida `POST /classify` da API FastAPI.

## Arquitetura

- [`support_agent.py`](support_agent.py):
  - `CUSTOMER_SUPPORT_SYSTEM_PROMPT`: define o papel de atendimento ao cliente, obriga a classificação prévia via ferramenta e orienta o tratamento das 5 intenções (`Refund Request`, `Technical Issue`, `Cancellation Request`, `Product Inquiry`, `Billing Inquiry`), além de pedir esclarecimento quando `probability < 0.50`.
  - `SupportDeskClient`: cliente HTTP assíncrono que autentica em `POST /auth/token`, mantém o JWT em cache dentro da validade (evitando atingir o rate limit de `10 req/min` do login) e renova automaticamente caso receba `HTTP 401`.
  - `classify_customer_intent` (`@function_tool`): envia o texto do usuário para `POST /classify` com `Authorization: Bearer <token>` e devolve `{"intent", "probability"}`.
  - `build_groq_model`: instancia `AsyncOpenAI(base_url="https://api.groq.com/openai/v1")` + `OpenAIChatCompletionsModel(model="openai/gpt-oss-20b")` e desabilita o tracing para a OpenAI (`set_tracing_disabled(True)`).
- [`demo_3_turns.py`](demo_3_turns.py): executa uma conversa contínua de **3 turnos** com `Runner.run` preservando o histórico via `result.to_input_list()`.

## Configuração e execução

1. Instale as dependências no ambiente virtual (a partir da raiz do repositório):

```bash
pip install -r agent/requirements.txt
```

2. Crie `agent/.env` a partir de [`agent/.env.example`](.env.example) e preencha `GROQ_API_KEY` e as credenciais da API (`SUPPORTDESK_API_USERNAME` / `SUPPORTDESK_API_PASSWORD`):

```bash
cp agent/.env.example agent/.env
```

3. Com a API FastAPI rodando (local em `http://localhost:8000` ou em produção em `https://supportdesk-api.marcosryan.com`), execute os 3 turnos:

```bash
python -m agent.demo_3_turns --save-transcript agent/conversa_3_turnos.md
```

Para conversar interativamente:

```bash
python -m agent.demo_3_turns --interactive
```

## Roteiro dos 3 turnos de demonstração

| Turno | Mensagem do cliente | Chamada esperada (`POST /classify`) | Comportamento do agente |
|---|---|---|---|
| **1** | *"Olá! Meu fone Bluetooth chegou ontem, mas não liga e a luz de carga nem acende."* | `classify_customer_intent` → `/classify` | Classifica a intenção/probabilidade, acolhe o relato e orienta diagnóstico inicial ou coleta de dados. |
| **2** | *"Já testei dois cabos USB-C diferentes e deixei 1 hora na tomada, sem sinal de vida. Quero meu dinheiro de volta."* | `classify_customer_intent` → `/classify` | Mantém o contexto do fone com defeito do Turno 1 e conduz o fluxo de reembolso/devolução. |
| **3** | *"Obrigado! Antes de finalizar o reembolso, também notei duas cobranças na minha fatura do cartão. Como verifico isso?"* | `classify_customer_intent` → `/classify` | Reutiliza o JWT em cache sem relogar desnecessariamente e trata a dúvida de faturamento sem perder o histórico do reembolso. |

## Testes automatizados

Os testes em [`tests/test_agent.py`](tests/test_agent.py) validam o ciclo completo (cache/renovação de JWT, chamada da `@function_tool` contra o endpoint `POST /classify` real via `httpx.ASGITransport` e conversa de 3 turnos no `Runner.run`):

```bash
python -m pytest agent/tests/ -v
```
