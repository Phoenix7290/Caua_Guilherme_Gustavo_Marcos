"""Testes unitários e de integração do agente SupportDesk (Item 4 - TP4)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import bcrypt
import httpx
import pytest
from agents import Runner, TResponseInputItem, set_tracing_disabled
from agents.items import ModelResponse
from agents.models.interface import Model
from agents.tool_context import ToolContext
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)
from sqlmodel import Session, SQLModel, create_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
FASTAPI_DIR = REPO_ROOT / "fastapi"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef")

from agent.support_agent import (  # noqa: E402
    SupportDeskAPIError,
    SupportDeskClient,
    SupportDeskConfig,
    build_support_agent,
    make_classify_tool,
)
from database import get_session  # noqa: E402
from limiter import limiter  # noqa: E402
from main import app  # noqa: E402
from models.tables import User  # noqa: E402
from security.auth import create_access_token  # noqa: E402

set_tracing_disabled(True)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def api_transport(tmp_path):
    """Cria banco temporário e retorna ASGITransport ligado à API FastAPI real."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'agent_test.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    pw_hash = bcrypt.hashpw(b"alice123", bcrypt.gensalt()).decode()
    with Session(engine) as session:
        session.add(User(username="alice", hashed_password=pw_hash))
        session.commit()

    def _override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    yield httpx.ASGITransport(app=app)
    app.dependency_overrides.clear()


class _FakeThreeTurnModel(Model):
    """Modelo determinístico que aciona a tool /classify a cada turno do usuário."""

    def __init__(self) -> None:
        self.calls = 0

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any = None,
    ) -> ModelResponse:
        self.calls += 1
        items = input if isinstance(input, list) else []

        # Se o último item já for a saída da tool, devolve a resposta final ao cliente.
        if items and items[-1].get("type") == "function_call_output":
            tool_payload = json.loads(items[-1]["output"])
            reply = (
                f"Intenção identificada: {tool_payload['intent']} "
                f"(confiança {tool_payload['probability']:.2f})."
            )
            return ModelResponse(
                output=[
                    ResponseOutputMessage(
                        id=f"msg_{self.calls}",
                        type="message",
                        role="assistant",
                        status="completed",
                        content=[
                            ResponseOutputText(
                                type="output_text",
                                text=reply,
                                annotations=[],
                            )
                        ],
                    )
                ],
                usage=Usage(),
                response_id=f"resp_{self.calls}",
            )

        # Caso contrário, extrai a última mensagem do usuário e chama `classify_customer_intent`.
        last_user_text = str(input) if isinstance(input, str) else ""
        for item in reversed(items):
            if item.get("role") == "user":
                content = item.get("content", "")
                last_user_text = (
                    content if isinstance(content, str) else str(content)
                )
                break

        return ModelResponse(
            output=[
                ResponseFunctionToolCall(
                    id=f"fc_{self.calls}",
                    call_id=f"call_{self.calls}",
                    type="function_call",
                    name="classify_customer_intent",
                    arguments=json.dumps({"text": last_user_text}),
                )
            ],
            usage=Usage(),
            response_id=f"resp_{self.calls}",
        )

    def stream_response(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_client_authenticates_and_caches_jwt(api_transport):
    client = SupportDeskClient(
        base_url="http://testserver",
        username="alice",
        password="alice123",
        transport=api_transport,
    )
    try:
        token_1 = await client.get_token()
        token_2 = await client.get_token()
        assert token_1 == token_2

        res = await client.classify("I want a refund for my broken headphones")
        assert set(res) == {"intent", "probability"}
        assert 0.0 < res["probability"] <= 1.0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_client_refreshes_expired_jwt_on_401(api_transport):
    expired_token = create_access_token({"sub": "alice"}) + "tampered"
    client = SupportDeskClient(
        base_url="http://testserver",
        username="alice",
        password="alice123",
        initial_token=expired_token,
        transport=api_transport,
    )
    try:
        res = await client.classify("My billing invoice has a duplicate charge")
        assert "intent" in res
        assert client._token != expired_token
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_client_validates_text_and_missing_credentials(api_transport):
    client = SupportDeskClient(
        base_url="http://testserver",
        transport=api_transport,
    )
    try:
        with pytest.raises(ValueError):
            await client.classify("   ")
        with pytest.raises(ValueError):
            await client.classify("a" * 2001)
        with pytest.raises(SupportDeskAPIError):
            await client.classify("Qual o prazo de entrega?")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_classify_tool_invokes_real_classify_endpoint(api_transport):
    client = SupportDeskClient(
        base_url="http://testserver",
        username="alice",
        password="alice123",
        transport=api_transport,
    )
    tool = make_classify_tool(client)
    args_json = json.dumps({"text": "Please cancel my subscription"})
    ctx = ToolContext(
        context=None,
        tool_name=tool.name,
        tool_call_id="call_test",
        tool_arguments=args_json,
    )
    try:
        raw_output = await tool.on_invoke_tool(ctx, args_json)
        parsed = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        assert set(parsed) == {"intent", "probability"}
        assert isinstance(parsed["intent"], str)
    finally:
        await client.aclose()


def test_build_support_agent_uses_groq_gpt_oss_20b():
    cfg = SupportDeskConfig(
        api_url="http://localhost:8000",
        username="alice",
        password="alice123",
        jwt_token=None,
        groq_api_key="gsk_test_dummy_key",
    )
    agent, _ = build_support_agent(config=cfg)
    assert agent.name == "SupportDesk Assistant"
    assert agent.model.model == "openai/gpt-oss-20b"
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "classify_customer_intent"


@pytest.mark.asyncio
async def test_three_turn_conversation_with_runner(api_transport):
    cfg = SupportDeskConfig(
        api_url="http://testserver",
        username="alice",
        password="alice123",
        jwt_token=None,
        groq_api_key=None,
    )
    fake_model = _FakeThreeTurnModel()
    agent, client = build_support_agent(
        config=cfg,
        model=fake_model,
        transport=api_transport,
    )

    turns = [
        "Meu fone Bluetooth não liga mais.",
        "Já tentei carregar e nada, quero reembolso.",
        "Também notei cobrança duplicada na fatura.",
    ]
    history: list[TResponseInputItem] = []

    try:
        for idx, message in enumerate(turns, start=1):
            turn_input: str | list[TResponseInputItem] = (
                message if not history else [*history, {"role": "user", "content": message}]
            )
            result = await Runner.run(agent, turn_input)
            history = result.to_input_list()
            assert "Intenção identificada:" in str(result.final_output)
            assert any(
                getattr(item, "type", "") == "tool_call_output_item"
                for item in result.new_items
            )
            assert len(history) >= idx * 3
    finally:
        await client.aclose()
