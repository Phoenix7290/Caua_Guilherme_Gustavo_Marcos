# Planejamento do Modelo de Classificação e do Teste Adversarial — TP3

**Projeto:** Customer Support Intent API  
**Disciplina:** Projeto de Bloco de Análise e Segurança de Agentes de IA (PB-Fastapi)  
**Repositório:** `Phoenix7290/Caua_Guilherme_Gustavo_Marcos`  
**Autor:** Marcos Ryan  
**Etapa:** TP3 — Transição Trimestre 1 / Trimestre 2  

---

## 1. Contexto e Objetivos

Este documento formaliza o planejamento para a próxima fase do projeto (Trimestre 2), que engloba a implementação de um modelo preditivo de Machine Learning na API FastAPI e a preparação da infraestrutura para os testes de invasão e ataques adversariais (pentest cruzado) previstos nos TPs subsequentes (TP4 e TP5).

A transição parte de uma API com stub heurístico rule-based e base de dados persistente com SQLite/SQLModel para um serviço com inferência estatística real baseada em Processamento de Linguagem Natural (PLN).

---

## 2. Modelo Candidato para Classificação de Intenções

### 2.1. Algoritmo Selecionado: Regressão Logística Multinomial (*Multinomial Logistic Regression*)
- **Biblioteca:** `scikit-learn` (`sklearn.linear_model.LogisticRegression`)
- **Configuração:** `multi_class='multinomial'`, `solver='lbfgs'`, `class_weight='balanced'`, regularização $L_2$.
- **Modelo de Comparação / Baseline:** Support Vector Classifier Linear (`LinearSVC(dual='auto', C=1.0)`).

### 2.2. Justificativa Técnica da Escolha

1. **Adequação a Espaços Vetoriais Esparsos e de Alta Dimensionalidade:**  
   Vetores gerados por contagem de termos em texto produzem matrizes esparsas onde o número de atributos (vocabulário) é grande frente ao número de termos por documento. Modelos lineares como Regressão Logística e SVM apresentam excelente desempenho analítico e convergência convexa estável nesses cenários.

2. **Probabilidades Calibradas para o Atributo `confidence` da API:**  
   O endpoint `POST /predict` retorna contratualmente o campo `confidence` (float entre 0.0 e 1.0). A Regressão Logística calcula a função *Softmax* sobre os logits das classes:
   $$P(y = c \mid \mathbf{x}) = \frac{e^{\mathbf{w}_c^T \mathbf{x} + b_c}}{\sum_{j=1}^{K} e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$
   Isso permite que a API forneça um escore de confiança estatisticamente fundamentado para cada predição, viabilizando regras de triagem (ex.: encaminhar para operador humano se $confidence < 0.70$).

3. **Interpretabilidade e Transparência dos Coeficientes:**  
   Diferente de modelos black-box (redes neurais profundas), os coeficientes $\mathbf{w}_c$ da Regressão Logística são diretamente interpretáveis. É possível mapear os n-gramas com maior peso positivo ou negativo para cada uma das 5 intenções (`Refund request`, `Technical issue`, `Cancellation request`, `Product inquiry`, `Billing inquiry`).

4. **Baixa Latência e Eficiência Operacional em Produção:**  
   A inferência da Regressão Logística consiste em um produto escalar simples ($\mathbf{w}^T \mathbf{x}$), consumindo menos de 2 milissegundos por chamada e ocupando poucos megabytes em memória RAM, ideal para execução estável no Raspberry Pi 5.

---

## 3. Estratégia de Representação do Texto: `CountVectorizer`

### 3.1. Técnica e Parametrização Arquitetural
- **Técnica:** `sklearn.feature_extraction.text.CountVectorizer`
- **Configuração Proposta:**
  - `ngram_range=(1, 2)`: extração de unigramas e bigramas.
  - `stop_words='english'`: remoção de palavras funcionais com baixo conteúdo semântico.
  - `min_df=2`: descarte de termos com frequência absoluta inferior a 2 (filtragem de typos espúrios).
  - `max_df=0.95`: descarte de palavras que apareçam em mais de 95% dos chamados.
  - `lowercase=True` e `strip_accents='unicode'`: normalização de caixa e acentuação.

### 3.2. Justificativa Técnica da Escolha

1. **Captura de Expressões-Chave via Bigramas:**  
   A análise exploratória (EDA) demonstrou que palavras isoladas podem ser ambíguas, enquanto pares de palavras contêm forte sinal de intenção em chamados de suporte (ex.: `"money back"`, `"cancel subscription"`, `"defective screen"`, `"billing error"`). O intervalo `(1, 2)` captura essas composições mantendo o vocabulário controlável.

2. **Determinismo e Pipeline Leve:**  
   A matriz documento-termo é determinística e gerada puramente por contagem de frequência de termos. Isso elimina o overhead de modelos de embeddings pesados no runtime da API e mantém a serialização (via `pickle` ou `joblib`) em tamanho reduzido.

3. **Facilidade de Rastreabilidade para Ataques Adversariais:**  
   Na etapa de pentest adversarial (TP4/TP5), atacantes manipularão palavras para enganar o classificador (*word substitution*, *perturbation attacks*). Com `CountVectorizer`, a análise de sensibilidade e auditoria de perturbação é direta, permitindo identificar com precisão quais palavras alteraram os vetores de entrada.

---

## 4. Alvo Autorizado para o Teste Adversarial (Pentest TP4/TP5)

### 4.1. Alvo Principal (Ambiente de Produção)
- **URL Base:** `https://supportdesk-api.marcosryan.com`
- **Hospedagem:** Raspberry Pi 5 (Ubuntu Server 24.04 LTS), isolado em rede local e exposto publicamente via **Cloudflare Zero Trust Tunnel** (`desktop-cloudflared`).
- **Protocolo:** HTTPS (TLS 1.3 obrigatório com HSTS).

### 4.2. Alvo Secundário / Homologação Local
- **URL Base:** `http://localhost:8000`
- **Execução:** Contêiner Docker Compose local (`fastapi/compose.yml`) com mapeamento de porta `8000:8000`.

### 4.3. Escopo e Endpoints Autorizados para Testes Adversariais

| Endpoint | Método | Autenticação | Controles e Limites Ativos |
|---|---|---|---|
| `/health` | `GET` | Aberto | Verificação de disponibilidade e uptime da aplicação. |
| `/auth/token` | `POST` | Aberto (Form) | Autenticação via usuário/senha. **Rate limiting estrito de 10 req/min por IP** (SlowAPI). Tentativas de brute-force serão bloqueadas com HTTP 429. |
| `/predict` | `POST` | Bearer JWT | Classificação de mensagens. **Alvo primário para ataques de evasão adversarial** (manipulação de payload de texto). Validação estrita de schema com `extra='forbid'` (HTTP 422). |
| `/predict` | `GET` | Bearer JWT | Listagem de predições pertencentes exclusivamente ao usuário autenticado. |
| `/predict/{id}` | `GET` | Bearer JWT | Consulta de predição específica por ID. **Mitigação de BOLA**: IDs de terceiros retornam HTTP 404 (evitando enumeração de recursos). |
| `/docs` | `GET` | Aberto | Documentação Swagger UI com Content-Security-Policy (CSP) estrita com hash SHA-256 de scripts. |

### 4.4. Regras de Engajamento e Segurança
1. **Negação de Serviço Volumétrico (DDoS):** Ataques volumétricos contra a infraestrutura de rede são proibidos; o foco do teste deve ser **adversarial machine learning** (evasão, manipulação de texto, poisoned inputs) e **vulnerabilidades de API** (OWASP API Top 10).
2. **Monitoramento e Logs:** Todas as tentativas de requisição inválida, rate limit excedido e violação de autorização são registradas nos logs do Uvicorn e do túnel Cloudflare.
3. **Credenciais Autorizadas para Testes:**
   - Usuário 1: `admin` / Senha: `admin123`
   - Usuário 2: `alice` / Senha: `alice123`
