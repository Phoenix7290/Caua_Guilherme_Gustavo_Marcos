import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limiter import limiter
from security.headers import install_docs, install_security_headers
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.predict import router as predict_router
from routes.classify import router as classify_router

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"


def create_app(is_production: bool | None = None) -> FastAPI:
    """Cria e configura a instância FastAPI com middlewares de segurança."""
    prod = (
        IS_PRODUCTION
        if is_production is None
        else is_production
    )
    application = FastAPI(
        title="Customer Support Intent API",
        description="API de classificação de intenção de tickets de suporte ao cliente.",
        version="1.0.0",
        docs_url=None,   # /docs é servido por install_docs fora de produção
        redoc_url=None,  # ReDoc removido: exige CSP frouxa (unsafe-inline) e não é usado
        openapi_url=None if prod else "/openapi.json",
    )

    env_origins = os.getenv("ALLOWED_ORIGINS")
    if env_origins:
        allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
    else:
        allowed_origins = DEFAULT_ALLOWED_ORIGINS

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    install_security_headers(application)
    if not prod:
        install_docs(application)

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(predict_router)
    application.include_router(classify_router)
    return application


DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://supportdesk-api.marcosryan.com",
]

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
