"""Agente de atendimento ao cliente com OpenAI Agents SDK + Groq.

Integra o OpenAI Agents SDK (`Agent`, `Runner`, `@function_tool`) ao provedor
Groq (`openai/gpt-oss-20b` via endpoint compatível com OpenAI) e consome a rota
protegida `POST /classify` da API FastAPI usando autenticação JWT.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from agents import (
    Agent,
    Model,
    OpenAIChatCompletionsModel,
    function_tool,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_API_URL = "http://localhost:8000"
MAX_TEXT_LENGTH = 2000
TOKEN_TTL_SECONDS = 14 * 60  # renova antes dos 15 min padrão do JWT

CUSTOMER_SUPPORT_SYSTEM_PROMPT = """Você é o assistente virtual de atendimento ao cliente da SupportDesk.

Regras de atendimento:
1. Sempre que o usuário relatar um problema, dúvida, pedido de reembolso, cancelamento ou questão de cobrança/fatura, chame primeiro a ferramenta `classify_customer_intent` com o texto da mensagem do usuário antes de formular sua resposta.
2. Analise a intenção prevista (`intent`) e o nível de confiança (`probability`) retornados pela API:
   - `Refund Request`: oriente sobre política de devolução/estorno e peça o número do pedido para encaminhar o reembolso.
   - `Technical Issue`: acolha o problema, peça detalhes técnicos objetivos (modelo, erro exibido, sistema) e sugira verificação inicial.
   - `Cancellation Request`: confirme o pedido de cancelamento, informe possíveis impactos (ex.: prazo ou estorno) e peça confirmação antes de concluir.
   - `Product Inquiry`: responda com clareza sobre características, compatibilidade ou disponibilidade e pergunte se deseja mais detalhes.
   - `Billing Inquiry`: auxilie em dúvidas de fatura, cobrança duplicada ou forma de pagamento, pedindo o identificador da cobrança quando necessário.
3. Se `probability` for baixa (< 0.50), mencione de forma transparente que pode haver mais de uma interpretação e faça uma pergunta curta para confirmar o objetivo do cliente.
4. Mantenha o contexto entre todos os turnos da conversa, responda no mesmo idioma do cliente (português ou inglês) de forma educada e concisa.
5. Nunca invente status de pedidos, valores ou políticas internas e nunca exponha tokens, credenciais ou detalhes internos da API."""


@dataclass(frozen=True)
class SupportDeskConfig:
    """Configurações de conexão com a API SupportDesk e provedor Groq."""

    api_url: str
    username: str | None
    password: str | None
    jwt_token: str | None
    groq_api_key: str | None
    groq_base_url: str = DEFAULT_GROQ_BASE_URL
    groq_model: str = DEFAULT_GROQ_MODEL

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "SupportDeskConfig":
        """Carrega configuração a partir do ambiente (e opcionalmente de um .env)."""
        if env_file is not None:
            load_dotenv(dotenv_path=env_file, override=False)
        else:
            default_env = Path(__file__).resolve().parent / ".env"
            if default_env.exists():
                load_dotenv(dotenv_path=default_env, override=False)
            else:
                load_dotenv(override=False)

        return cls(
            api_url=os.getenv("SUPPORTDESK_API_URL", DEFAULT_API_URL).rstrip("/"),
            username=os.getenv("SUPPORTDESK_API_USERNAME") or None,
            password=os.getenv("SUPPORTDESK_API_PASSWORD") or None,
            jwt_token=os.getenv("SUPPORTDESK_JWT_TOKEN") or None,
            groq_api_key=os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or None,
            groq_base_url=(
                os.getenv("LLM_BASE_URL")
                or os.getenv("GROQ_BASE_URL")
                or DEFAULT_GROQ_BASE_URL
            ).rstrip("/"),
            groq_model=(
                os.getenv("LLM_MODEL")
                or os.getenv("GROQ_MODEL")
                or DEFAULT_GROQ_MODEL
            ),
        )


class SupportDeskAPIError(RuntimeError):
    """Erro de comunicação ou autenticação com a API SupportDesk."""


class SupportDeskClient:
    """Cliente HTTP assíncrono com cache e renovação automática de JWT."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_URL,
        username: str | None = None,
        password: str | None = None,
        initial_token: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token = initial_token
        self._token_expires_at = (
            time.monotonic() + TOKEN_TTL_SECONDS if initial_token else 0.0
        )
        self._timeout = timeout
        self._transport = transport
        self._http: httpx.AsyncClient | None = None

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            kwargs: dict[str, Any] = {
                "base_url": self.base_url,
                "timeout": self._timeout,
            }
            if self._transport is not None:
                kwargs["transport"] = self._transport
            self._http = httpx.AsyncClient(**kwargs)
        return self._http

    async def aclose(self) -> None:
        """Fecha o cliente HTTP subjacente."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()

    def _has_valid_cached_token(self) -> bool:
        return bool(self._token) and time.monotonic() < self._token_expires_at

    async def authenticate(self) -> str:
        """Obtém um novo token Bearer em POST /auth/token."""
        if not self.username or not self.password:
            raise SupportDeskAPIError(
                "Credenciais da API ausentes: defina SUPPORTDESK_JWT_TOKEN ou "
                "SUPPORTDESK_API_USERNAME e SUPPORTDESK_API_PASSWORD."
            )

        client = self._get_http()
        response = await client.post(
            "/auth/token",
            data={"username": self.username, "password": self.password},
        )
        if response.status_code != 200:
            raise SupportDeskAPIError(
                f"Falha ao autenticar em /auth/token (HTTP {response.status_code})."
            )

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise SupportDeskAPIError("Resposta de /auth/token não contém access_token.")

        self._token = token
        self._token_expires_at = time.monotonic() + TOKEN_TTL_SECONDS
        return token

    async def get_token(self, force_refresh: bool = False) -> str:
        """Retorna JWT em cache ou autentica quando ausente/expirado."""
        if not force_refresh and self._has_valid_cached_token():
            assert self._token is not None
            return self._token
        return await self.authenticate()

    async def classify(self, text: str) -> dict[str, Any]:
        """Envia o texto para POST /classify e retorna intent + probability."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("O texto para classificação não pode ser vazio.")
        if len(cleaned) > MAX_TEXT_LENGTH:
            raise ValueError(
                f"O texto excede o limite de {MAX_TEXT_LENGTH} caracteres da API."
            )

        token = await self.get_token()
        client = self._get_http()
        response = await client.post(
            "/classify",
            json={"text": cleaned},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Se o token expirou ou foi invalidado, tenta renovar uma vez quando há credenciais.
        if response.status_code == 401 and self.username and self.password:
            token = await self.get_token(force_refresh=True)
            response = await client.post(
                "/classify",
                json={"text": cleaned},
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code != 200:
            raise SupportDeskAPIError(
                f"Erro ao chamar POST /classify (HTTP {response.status_code})."
            )

        data = response.json()
        return {
            "intent": str(data["intent"]),
            "probability": round(float(data["probability"]), 4),
        }


def make_classify_tool(client: SupportDeskClient):
    """Cria a @function_tool vinculada ao cliente autenticado da SupportDesk API."""

    @function_tool
    async def classify_customer_intent(text: str) -> str:
        """Classifica a intenção de uma mensagem de atendimento ao cliente via POST /classify.

        Args:
            text: Texto original da solicitação ou pergunta enviada pelo cliente.

        Returns:
            JSON com `intent` (categoria prevista) e `probability` (confiança 0..1).
        """
        result = await client.classify(text)
        return json.dumps(result, ensure_ascii=False)

    return classify_customer_intent


def build_groq_model(
    api_key: str | None = None,
    model_name: str = DEFAULT_GROQ_MODEL,
    base_url: str = DEFAULT_GROQ_BASE_URL,
) -> OpenAIChatCompletionsModel:
    """Configura provedor compatível com OpenAI (Groq, Ollama, etc.) para o Agents SDK."""
    resolved_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "Chave de LLM não configurada. Defina LLM_API_KEY/GROQ_API_KEY no ambiente ou em agent/.env "
            "(para Ollama local, use LLM_API_KEY='ollama' e LLM_BASE_URL='http://localhost:11434/v1')."
        )

    # Desabilita o envio de traces para a OpenAI quando usando chave Groq.
    set_tracing_disabled(True)

    groq_client = AsyncOpenAI(
        api_key=resolved_key,
        base_url=base_url.rstrip("/"),
    )
    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=groq_client,
    )


def build_support_agent(
    config: SupportDeskConfig | None = None,
    model: Model | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[Agent, SupportDeskClient]:
    """Constrói o Agent de atendimento ao cliente e o cliente HTTP da API."""
    cfg = config or SupportDeskConfig.from_env()
    client = SupportDeskClient(
        base_url=cfg.api_url,
        username=cfg.username,
        password=cfg.password,
        initial_token=cfg.jwt_token,
        transport=transport,
    )
    resolved_model = model or build_groq_model(
        api_key=cfg.groq_api_key,
        model_name=cfg.groq_model,
        base_url=cfg.groq_base_url,
    )
    agent = Agent(
        name="SupportDesk Assistant",
        instructions=CUSTOMER_SUPPORT_SYSTEM_PROMPT,
        model=resolved_model,
        tools=[make_classify_tool(client)],
    )
    return agent, client
