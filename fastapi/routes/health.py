from fastapi import APIRouter
from models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Verifica se a API está ativa e funcionando corretamente."""
    return HealthResponse(status="ok", version="1.0.0")
