import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.predict import router as predict_router

app = FastAPI(
    title="Customer Support Intent API",
    description="API de classificação de intenção de tickets de suporte ao cliente.",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(predict_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
