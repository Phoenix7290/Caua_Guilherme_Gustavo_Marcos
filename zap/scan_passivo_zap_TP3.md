# Relatório de Auditoria de Segurança com OWASP ZAP — TP3

**Projeto:** Customer Support Intent API  
**Disciplina:** Projeto de Bloco de Análise e Segurança de Agentes de IA (PB-Fastapi)  
**Repositório:** `Phoenix7290/Caua_Guilherme_Gustavo_Marcos`  
**Autor:** Marcos Ryan  
**Ferramenta:** OWASP ZAP (ZAP API Scan Docker `zaproxy/zap-stable:latest`)  
**Data da Auditoria:** 26 de Outubro de 2026  
**Alvo Auditado:** `http://localhost:8000/openapi.json` / `http://localhost:8000/docs`  

---

## 1. Resumo Executivo da Auditoria

Em conformidade com a Tarefa 5 do enunciado do TP3, foi realizada a auditoria final de segurança da API FastAPI em tempo de execução utilizando o **OWASP ZAP**.

O scan passivo de API (`zap-api-scan.py`) importou com sucesso a totalidade das definições da API a partir do endpoint `/openapi.json`, cobrindo 7 URLs e avaliando mais de 118 regras ativas e passivas de segurança (incluindo SQL Injection, Cross-Site Scripting, Directory Browsing, Information Disclosure, Broken Authentication, CORS e cabeçalhos HTTP).

### Resultado Consolidado de Findings:
- **Alertas de Severidade High:** **0 (zero)**
- **Alertas de Severidade Medium:** **0 (zero)**
- **Alertas de Severidade Low:** **0 (zero)** *(após adição do header `Cross-Origin-Resource-Policy: same-origin`)*
- **Alertas de Severidade Informational:** **4 (quatro)**

> **Declaração Formal de Conformidade:**  
> Conforme exigido pela especificação do TP3 (*"Caso não existam findings Medium ou High, essa informação deve ser explicitamente documentada"*), **certifica-se que nenhum alerta de risco Alto (High), Médio (Medium) ou Baixo (Low) permanece na aplicação**. Todos os controles preventivos implementados foram validados com `0 FAIL` e `0 WARN` no OWASP ZAP.

---

## 2. Detalhamento dos Alertas Identificados e Correções Aplicadas

Abaixo estão detalhados os alertas analisados durante a auditoria com o OWASP ZAP:

| Alerta | Severidade Inicial | Status Final | URLs Afetadas | Análise de Risco e Correção Realizada |
|---|---|---|---|---|
| **Cross-Origin-Resource-Policy Header Missing or Invalid (`[90004]`)** | **Low** | **Corrigido (PASS)** | `/health`, `/openapi.json` | O cabeçalho CORP previne vazamentos de canais laterais (*Spectre*) ao restringir quem pode carregar recursos da API. **Correção:** Adicionado `"Cross-Origin-Resource-Policy": "same-origin"` em `fastapi/security/headers.py`. |
| **Cross-Domain Misconfiguration / CORS Wildcard (`[10098]`)** | **Medium (Preventivo)** | **Corrigido (PASS)** | Todas as rotas | Uso de `allow_origins=["*"]` expõe a API a requisições cross-origin arbitrárias. **Correção:** Configurada allowlist explícita (`DEFAULT_ALLOWED_ORIGINS`) sem wildcard em `fastapi/main.py`. |
| **A Client Error response code was returned by the server** | **Informational** | **Esperado (PASS)** | `/predict`, `/predict/1` | Indica que o servidor retornou código HTTP `401 Unauthorized` durante as tentativas de requisição sem token Bearer. **Comportamento esperado e desejado**, validando a eficácia da autenticação obrigatória nas rotas protegidas. |
| **Authentication Request Identified** | **Informational** | **Esperado (PASS)** | `/auth/token` | O ZAP identificou formalmente a rota `/auth/token` como endpoint de autenticação. Confirma conformidade com o padrão OAuth2 Password Flow. |
| **Non-Storable Content / Storable Content** | **Informational** | **Esperado (PASS)** | Rotas da API | Indica que as respostas autenticadas não são armazenadas em cache por proxies intermediários, prevenindo exposição de dados sensíveis. |

---

## 3. Controles de Segurança Implementados e Mitigações Ativas

A ausência de vulnerabilidades de severidade Alta e Média na aplicação é resultado da adoção rigorosa de práticas de *Security by Design* nas camadas do FastAPI:

### 3.1. Mitigação de Cross-Site Scripting (XSS) e Injeção de Scripts no `/docs`
- **Controle:** Middleware `install_security_headers` e rota customizada `install_docs` em `fastapi/security/headers.py`.
- **Implementação:** A documentação interativa Swagger UI calcula o hash SHA-256 do script inline do Swagger e aplica uma `Content-Security-Policy` estrita:
  ```text
  default-src 'none'; script-src 'sha256-...' https://cdn.jsdelivr.net; style-src https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'; base-uri 'none'; form-action 'none'
  ```
- **Evidência:** Regras de CSP do ZAP (`[10038]`, `[10055]`) e testes de injeção XSS passaram com status **PASS**.

### 3.2. Mitigação de Clickjacking e Downgrade de Protocolo
- **Controle:** Headers HTTP globais em `fastapi/security/headers.py`:
  - `X-Frame-Options: DENY` e `frame-ancestors 'none'` (anti-clickjacking).
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (força túnel HTTPS/TLS).
  - `X-Content-Type-Options: nosniff` (prevenção contra sniffing de MIME type).
- **Evidência:** Alertas ZAP `[10020]`, `[10021]` e `[10035]` validados com status **PASS**.

### 3.3. Mitigação de BOLA / IDOR (Broken Object Level Authorization — OWASP API1:2023)
- **Controle:** Validação estrita de ownership em `fastapi/routes/predict.py`.
- **Implementação:** Na consulta `GET /predict/{prediction_id}`, o sistema valida `if prediction.owner_id != current_user.id` e retorna **HTTP 404 (Not Found)** em vez de 403 Forbidden.
- **Evidência:** Coberto pela suíte pytest (`test_acesso_a_recurso_de_outro_usuario_retorna_404`), impedindo que atacantes descubram IDs de outros clientes por enumeração.

### 3.4. Mitigação de Mass Assignment / Overposting (OWASP API3:2023)
- **Controle:** Schemas Pydantic em `fastapi/models/schemas.py` com `model_config = ConfigDict(extra="forbid")`.
- **Implementação:** Requisições que tentem injetar parâmetros espúrios (como `owner_id`, `role` ou `is_admin`) são sumariamente rejeitadas com **HTTP 422 Unprocessable Entity**.
- **Evidência:** Validado por `test_campo_extra_no_body_e_rejeitado`.

### 3.5. Mitigação de Força Bruta (Anti-Brute Force via SlowAPI)
- **Controle:** Rate limiting aplicado ao endpoint de login em `fastapi/routes/auth.py`.
- **Implementação:** `@limiter.limit("10/minute")` por endereço IP cliente.
- **Evidência:** Validado por `test_rate_limit_no_login_bloqueia_com_429`.

---

## 4. Auditoria da Documentação Interativa `/docs`

A documentação interativa em `/docs` foi auditada para garantir total clareza operacional para desenvolvedores e clientes da API:

1. **Descrição das Operações:** Cada endpoint conta com sumário executivo (`summary`) e docstrings detalhadas descrevendo objetivo, lógica de negócio e requisitos técnicos.
2. **Parâmetros e Corpo Esperado:**
   - `/auth/token`: formulário OAuth2 (`username`, `password`).
   - `POST /predict`: schema JSON `PredictRequest` estritamente tipado (`text: str`).
   - `GET /predict/{prediction_id}`: parâmetro de rota inteiro validado.
3. **Mapeamento Explícito de Respostas HTTP:**
   - `200 OK`: esquemas de retorno documentados com modelos SQLModel/Pydantic (`HealthResponse`, `TokenResponse`, `PredictResponse`, `PredictionRead`).
   - `401 Unauthorized`: erro de credenciais ou token JWT ausente/expirado.
   - `404 Not Found`: recurso inexistente ou de outro proprietário (BOLA).
   - `422 Unprocessable Entity`: campos extras ou violações de validação de dados.
   - `429 Too Many Requests`: resposta padronizada de bloqueio por rate limiting.
4. **Mecanismo de Autenticação:** A rota `/auth/token` está integrada ao esquema `OAuth2PasswordBearer`, habilitando o fluxo nativo "Authorize" no Swagger UI para teste de rotas protegidas diretamente pelo navegador.

---

## 5. Artefatos de Entrega

Os relatórios gerados pela ferramenta foram consolidados no diretório `zap/` do repositório:
- [`zap/zap_report.html`](file:///home/ryanslx/code/Caua_Guilherme_Gustavo_Marcos/zap/zap_report.html): relatório interativo completo gerado pelo OWASP ZAP.
- [`zap/zap_report.json`](file:///home/ryanslx/code/Caua_Guilherme_Gustavo_Marcos/zap/zap_report.json): relatório estruturado em formato JSON para ingestão automatizada em pipelines de CI/CD.
