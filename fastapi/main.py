import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from limiter import limiter
from security.headers import install_docs, install_security_headers
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.predict import router as predict_router

app = FastAPI(
    title="Customer Support Intent API",
    description="API de classificação de intenção de tickets de suporte ao cliente.",
    version="1.0.0",
    docs_url=None,   # /docs é servido por install_docs (CSP restritiva)
    redoc_url=None,  # ReDoc removido: exige CSP frouxa (unsafe-inline) e não é usado
)

# ── Configuração de CORS com Allowlist Explícita (Sem Wildcard "*") ────────
# Corrige risco de Cross-Domain Misconfiguration (OWASP ZAP [10098]) e atende
# ao controle de allowlist explícita de origens exigido no TP2/TP3.
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://supportdesk-api.marcosryan.com",
]

env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

install_security_headers(app)
install_docs(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(predict_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
