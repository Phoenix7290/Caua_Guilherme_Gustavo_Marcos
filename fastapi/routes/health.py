from fastapi import APIRouter
from models.schemas import HealthResponse

router = APIRouter()

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Verificação de Saúde e Disponibilidade",
    responses={
        200: {
            "description": "API ativa, saudável e operacional.",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "version": "1.0.0"}
                }
            },
        }
    },
)
def health_check():
    """
    Verifica a disponibilidade operacional e a integridade da API FastAPI.
    
    Não requer autenticação.
    """
    return HealthResponse(status="ok", version="1.0.0")
