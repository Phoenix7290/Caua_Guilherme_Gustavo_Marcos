import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef")

from datetime import timedelta

import bcrypt
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from database import get_session
from limiter import AUTH_RATE_LIMIT, limiter
from main import app
from models.tables import Prediction, User
from security.auth import ALGORITHM, create_access_token


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
        admin, alice = User(username="admin", hashed_password=pw), User(username="alice", hashed_password=pw)
        s.add(admin); s.add(alice); s.commit()
        p_admin = Prediction(owner_id=admin.id, text="texto do admin", intent="Refund Request", confidence=0.9)
        p_alice = Prediction(owner_id=alice.id, text="texto da alice", intent="Billing Inquiry", confidence=0.85)
        s.add(p_admin); s.add(p_alice); s.commit()
        ids = {"admin": p_admin.id, "alice": p_alice.id}

    def _session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    yield TestClient(app), engine, ids
    app.dependency_overrides.clear()


def _auth(username: str) -> dict:

    return {"Authorization": f"Bearer {create_access_token({'sub': username})}"}


def test_acesso_sem_token_retorna_401(ctx):
    client, _, ids = ctx
    for method, url, kw in [
        ("GET", "/predict", {}),
        ("GET", f"/predict/{ids['admin']}", {}),
        ("POST", "/predict", {"json": {"text": "quero reembolso"}}),
    ]:
        r = client.request(method, url, **kw)
        assert r.status_code == 401, f"{method} {url} deveria exigir token"
        assert r.headers["www-authenticate"] == "Bearer"


def test_acesso_a_recurso_de_outro_usuario_retorna_404(ctx):
    client, _, ids = ctx

    r = client.get(f"/predict/{ids['admin']}", headers=_auth("alice"))
    assert r.status_code == 404
    assert "texto do admin" not in r.text

    r = client.get("/predict", headers=_auth("alice"))
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [ids["alice"]]

    assert client.get(f"/predict/{ids['alice']}", headers=_auth("alice")).status_code == 200


def test_campo_extra_no_body_e_rejeitado(ctx):
    client, engine, _ = ctx
    with Session(engine) as s:
        antes = len(s.exec(select(Prediction)).all())
    r = client.post(
        "/predict",
        headers=_auth("alice"),
        json={"text": "quero reembolso", "owner_id": 1, "is_admin": True},
    )
    assert r.status_code == 422
    assert {e["type"] for e in r.json()["detail"]} == {"extra_forbidden"}
    with Session(engine) as s:
        assert len(s.exec(select(Prediction)).all()) == antes


def test_login_credenciais_validas_retornam_token(ctx):
    client, _, ids = ctx
    r = client.post("/auth/token", data={"username": "alice", "password": "senha"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    r = client.get("/predict", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [ids["alice"]]


@pytest.mark.parametrize(
    "username, password",
    [
        ("alice", "senha-errada"),
        ("fantasma", "senha"),
    ],
)
def test_login_credenciais_invalidas_retornam_401(ctx, username, password):
    client, _, _ = ctx
    r = client.post("/auth/token", data={"username": username, "password": password})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert "access_token" not in r.json()

    assert r.json()["detail"] == "Usuário ou senha incorretos."


def test_rota_protegida_rejeita_tokens_invalidos(ctx):
    client, _, _ = ctx
    expirado = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=-1))
    assinatura_errada = jwt.encode({"sub": "alice"}, "outra-chave-qualquer", algorithm=ALGORITHM)
    usuario_inexistente = create_access_token({"sub": "fantasma"})
    sem_sub = create_access_token({"foo": "bar"})
    for nome, token in [
        ("expirado", expirado),
        ("assinatura forjada", assinatura_errada),
        ("usuário inexistente", usuario_inexistente),
        ("sem claim sub", sem_sub),
        ("lixo", "isto.nao.e-um-jwt"),
    ]:
        r = client.get("/predict", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, f"token {nome} deveria ser rejeitado"
        assert r.json()["detail"] == "Token inválido ou expirado."


@pytest.mark.parametrize(
    "body, tipo_erro",
    [
        ({}, "missing"),
        ({"text": 123}, "string_type"),
        ({"text": ["a", "b"]}, "string_type"),
        ({"text": None}, "string_type"),
    ],
)
def test_corpo_invalido_retorna_422(ctx, body, tipo_erro):
    client, engine, _ = ctx
    with Session(engine) as s:
        antes = len(s.exec(select(Prediction)).all())
    r = client.post("/predict", headers=_auth("alice"), json=body)
    assert r.status_code == 422
    assert r.json()["detail"][0]["type"] == tipo_erro
    with Session(engine) as s:
        assert len(s.exec(select(Prediction)).all()) == antes


def test_rate_limit_no_login_bloqueia_com_429(ctx):
    client, _, _ = ctx
    limite = int(AUTH_RATE_LIMIT.split("/")[0])
    credenciais = {"username": "alice", "password": "senha-errada"}


    for i in range(limite):
        r = client.post("/auth/token", data=credenciais)
        assert r.status_code == 401, f"requisição {i + 1} deveria passar pelo limiter"


    r = client.post("/auth/token", data=credenciais)
    assert r.status_code == 429
    assert "rate limit" in r.json()["error"].lower()


    r = client.post("/auth/token", data={"username": "alice", "password": "senha"})
    assert r.status_code == 429