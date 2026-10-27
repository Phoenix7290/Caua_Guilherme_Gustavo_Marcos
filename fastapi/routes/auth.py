from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from database import get_session
from limiter import AUTH_RATE_LIMIT, limiter
from models.schemas import TokenResponse
from security.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Autenticação e Obtenção de Token JWT",
    responses={
        200: {"description": "Autenticação bem-sucedida, retorna o token de acesso Bearer."},
        401: {"description": "Credenciais inválidas (usuário ou senha incorretos)."},
        422: {"description": "Dados de requisição inválidos ou campos ausentes."},
        429: {"description": "Muitas tentativas de login. Limite de requisições excedido (10 req/min)."},
    },
)
@limiter.limit(AUTH_RATE_LIMIT)  # anti brute force: 10 req/min por cliente
def login(
    request: Request,  # exigido pelo SlowAPI
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """
    Autentica o usuário via OAuth2 Password Flow e emite um JWT assinado com HS256.

    - **Entrada**: formulário `multipart/form-data` ou `application/x-www-form-urlencoded` com `username` e `password`.
    - **Proteção Anti-Brute-Force**: limitado a 10 requisições por minuto por cliente (SlowAPI).
    - **Retorno**: token Bearer para uso nas rotas protegidas (`Authorization: Bearer <token>`).
    """
    if not authenticate_user(session, form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)
