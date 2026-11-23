import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef")

from datetime import timedelta

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from database import get_session
from limiter import PREDICT_RATE_LIMIT, limiter
from main import app
from ml.model import get_model
from models.tables import Prediction, User
from security.auth import create_access_token


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def ctx(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    pw = bcrypt.hashpw(b"senha", bcrypt.gensalt()).decode()
    with Session(engine) as s:
        s.add(User(username="alice", hashed_password=pw))
        s.commit()

    def _session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def _auth(username: str = "alice", **kw) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': username}, **kw)}"}


def test_classify_sem_token_retorna_401(ctx):
    client, _ = ctx
    r = client.post("/classify", json={"text": "quero reembolso"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_classify_token_invalido_retorna_401(ctx):
    client, _ = ctx
    r = client.post(
        "/classify", json={"text": "oi"}, headers={"Authorization": "Bearer lixo.invalido.token"}
    )
    assert r.status_code == 401


def test_classify_token_expirado_retorna_401(ctx):
    client, _ = ctx
    headers = _auth(expires_delta=timedelta(minutes=-1))
    r = client.post("/classify", json={"text": "oi"}, headers=headers)
    assert r.status_code == 401


def test_classify_retorna_intent_e_probabilidade(ctx):
    client, _ = ctx
    r = client.post(
        "/classify", json={"text": "I want a refund for my order"}, headers=_auth()
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"intent", "probability"}
    assert body["intent"] in set(get_model().classes_)
    assert 0.0 < body["probability"] <= 1.0


def test_classify_nao_persiste_predicao(ctx):
    client, engine = ctx
    client.post("/classify", json={"text": "my invoice is wrong"}, headers=_auth())
    with Session(engine) as s:
        assert s.exec(select(Prediction)).all() == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": ""},
        {"text": 123},
        {"text": "x" * 2001},
        {"text": "oi", "owner_id": 1},
    ],
)
def test_classify_payload_invalido_retorna_422(ctx, payload):
    client, _ = ctx
    r = client.post("/classify", json=payload, headers=_auth())
    assert r.status_code == 422


def test_classify_rate_limit_retorna_429(ctx):
    client, _ = ctx
    limite = int(PREDICT_RATE_LIMIT.split("/")[0])
    codes = [
        client.post("/classify", json={"text": "oi"}, headers=_auth()).status_code
        for _ in range(limite + 1)
    ]
    assert codes[:limite] == [200] * limite
    assert codes[-1] == 429
