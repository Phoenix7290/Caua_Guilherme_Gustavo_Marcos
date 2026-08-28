from pydantic import BaseModel
from typing import Optional

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PredictRequest(BaseModel):
    text: str

class PredictResponse(BaseModel):
    intent: str
    confidence: float
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
