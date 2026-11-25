from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)


class PredictResponse(BaseModel):
    id: Optional[int] = None
    intent: str
    confidence: float
    message: str


class ClassifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)


class ClassifyResponse(BaseModel):
    intent: str
    probability: float


class PredictionRead(BaseModel):
    id: int
    text: str
    intent: str
    confidence: float
    created_at: str


class HealthResponse(BaseModel):
    status: str
    version: str
