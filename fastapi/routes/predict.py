import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from database import get_session
from models.schemas import PredictRequest, PredictResponse, PredictionRead
from models.tables import Prediction, User
from security.auth import get_current_user

router = APIRouter(prefix="/predict", tags=["Predict"])

_INTENT_RULES = [
    (r"\b(reembolso|reembolsar|devolu|refund|dinheiro de volta)\b", "Refund Request", 0.91),
    (r"\b(cancelar|cancelamento|cancel)\b", "Cancellation Request", 0.88),
    (r"\b(cobran|fatura|boleto|billing|invoice|charge)\b", "Billing Inquiry", 0.85),
    (
        r"\b(erro|bug|falha|crash|n[ãa]o funciona|technical|problema t[eé]cnico)\b",
        "Technical Issue",
        0.87,
    ),
    (r"\b(informa|d[úu]vida|como funciona|product|produto)\b", "Product Inquiry", 0.82),
]


def _classify(text: str):
    lower = text.lower()
    for pattern, intent, confidence in _INTENT_RULES:
        if re.search(pattern, lower):
            return intent, confidence
    return "Product Inquiry", 0.60


@router.post(
    "",
    response_model=PredictResponse,
    summary="Classificar Intenção do Ticket",
    responses={
        200: {"description": "Intenção classificada e persistida com sucesso para o usuário autenticado."},
        401: {"description": "Não autenticado ou token JWT ausente/inválido."},
        422: {"description": "Erro de validação (ex.: corpo vazio, tipo inválido ou campos adicionais rejeitados por extra='forbid')."},
    },
)
def predict(
    body: PredictRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Classifica a intenção da mensagem e persiste a predição associada ao `owner_id` do usuário autenticado.

    - **Autenticação**: obrigatória via Header `Authorization: Bearer <token>`.
    - **Validação Estrita**: campos extras no JSON são estritamente rejeitados com HTTP 422 (`extra='forbid'`).
    - **Prevenção de BOLA**: o `owner_id` é extraído diretamente do token validado, impedindo falsificação de propriedade.
    """
    intent, confidence = _classify(body.text)
    prediction = Prediction(
        owner_id=current_user.id,
        text=body.text,
        intent=intent,
        confidence=confidence,
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)
    return PredictResponse(
        id=prediction.id,
        intent=intent,
        confidence=confidence,
        message="Intenção classificada por stub rule-based (modelo ML pendente).",
    )


@router.get(
    "",
    response_model=list[PredictionRead],
    summary="Listar Predições do Usuário Autenticado",
    responses={
        200: {"description": "Lista de predições pertencentes ao usuário autenticado."},
        401: {"description": "Não autenticado ou token JWT ausente/inválido."},
    },
)
def list_predictions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Retorna a lista de predições pertencentes exclusivamente ao usuário autenticado.

    - **Autenticação**: obrigatória via Header `Authorization: Bearer <token>`.
    - **Isolamento Multitenant**: filtra explicitamente por `Prediction.owner_id == current_user.id`.
    """
    return session.exec(select(Prediction).where(Prediction.owner_id == current_user.id)).all()


@router.get(
    "/{prediction_id}",
    response_model=PredictionRead,
    summary="Consultar Predição por ID",
    responses={
        200: {"description": "Predição localizada e pertencente ao usuário solicitante."},
        401: {"description": "Não autenticado ou token JWT ausente/inválido."},
        404: {"description": "Predição não encontrada (ID inexistente ou pertencente a outro usuário - Mitigação BOLA)."},
    },
)
def get_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Retorna uma predição específica por ID caso ela pertença ao usuário autenticado.

    - **Autenticação**: obrigatória via Header `Authorization: Bearer <token>`.
    - **Mitigação BOLA (Broken Object Level Authorization - OWASP Top 10)**:
      Valida se `prediction.owner_id == current_user.id`. Se o ID não existir ou pertencer
      a outro usuário, responde uniformemente com **HTTP 404 (Not Found)** para evitar
      enumeração de recursos (Resource Enumeration / IDOR).
    """
    prediction = session.get(Prediction, prediction_id)
    if prediction is None or prediction.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Predição não encontrada.",
        )
    return prediction
