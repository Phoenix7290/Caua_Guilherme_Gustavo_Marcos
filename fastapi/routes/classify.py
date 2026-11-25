from fastapi import APIRouter, Depends, Request

from limiter import PREDICT_RATE_LIMIT, limiter
from ml.model import get_model
from models.schemas import ClassifyRequest, ClassifyResponse
from models.tables import User
from security.auth import get_current_user

router = APIRouter(prefix="/classify", tags=["Classify"])


@router.post(
    "",
    response_model=ClassifyResponse,
    summary="Classificar Intenção via Modelo Treinado",
    responses={
        200: {"description": "Intenção prevista pelo modelo com a respectiva probabilidade."},
        401: {"description": "Não autenticado ou token JWT ausente/inválido."},
        422: {"description": "Erro de validação (ex.: corpo vazio, tipo inválido ou campos adicionais rejeitados por extra='forbid')."},
        429: {"description": "Limite de requisições excedido (30 req/min)."},
    },
)
@limiter.limit(PREDICT_RATE_LIMIT)
def classify(
    request: Request,
    body: ClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Classifica a intenção da mensagem usando o modelo de ML treinado (TF-IDF + LogisticRegression).

    - **Autenticação**: obrigatória via Header `Authorization: Bearer <token>`.
    - **Validação Estrita**: campos extras no JSON são rejeitados com HTTP 422 (`extra='forbid'`).
    - **Stateless**: não persiste a predição; retorna apenas a intenção prevista e a probabilidade
      da classe de maior confiança (`predict_proba`).
    """
    model = get_model()
    proba = model.predict_proba([body.text])[0]
    idx = int(proba.argmax())
    return ClassifyResponse(
        intent=str(model.classes_[idx]),
        probability=float(proba[idx]),
    )
