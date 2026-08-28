import re
from fastapi import APIRouter, Depends

from models.schemas import PredictRequest, PredictResponse
from security.auth import get_current_user

router = APIRouter(prefix="/predict", tags=["Predict"])

_INTENT_RULES = [
    (r"\b(reembolso|reembolsar|devolu|refund|dinheiro de volta)\b", "Refund Request", 0.91),
    (r"\b(cancelar|cancelamento|cancel)\b",                          "Cancellation Request", 0.88),
    (r"\b(cobran|fatura|boleto|billing|invoice|charge)\b",           "Billing Inquiry", 0.85),
    (r"\b(erro|bug|falha|crash|n[ãa]o funciona|technical|problema t[eé]cnico)\b",
                                                                      "Technical Issue", 0.87),
    (r"\b(informa|d[úu]vida|como funciona|product|produto)\b",       "Product Inquiry", 0.82),
]

def _classify(text: str):
    lower = text.lower()
    for pattern, intent, confidence in _INTENT_RULES:
        if re.search(pattern, lower):
            return intent, confidence
    return "Product Inquiry", 0.60   


@router.post("/", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    current_user: str = Depends(get_current_user),
):
    intent, confidence = _classify(body.text)
    return PredictResponse(
        intent=intent,
        confidence=confidence,
        message=f"Intenção classificada por stub rule-based (modelo ML pendente).",
    )
