"""FastAPI inference service for AI-assisted complaint triage."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from ai_triage.train import predict, CATEGORIES, PRIORITIES

app = FastAPI(title="AI Complaint Triage", version="0.1.0")


class TriageRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=5000)

    @field_validator("title", "description")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class TriageResponse(BaseModel):
    category: str
    priority: str
    category_confidence: float | None = None
    priority_confidence: float | None = None
    abstain: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    result = predict(request.title, request.description)
    category_conf = result.get("category_confidence")
    priority_conf = result.get("priority_confidence")
    abstain = (category_conf is not None and category_conf < 0.5) or (
        priority_conf is not None and priority_conf < 0.5
    )
    return TriageResponse(
        category=result["category"],
        priority=result["priority"],
        category_confidence=category_conf,
        priority_confidence=priority_conf,
        abstain=abstain,
    )
