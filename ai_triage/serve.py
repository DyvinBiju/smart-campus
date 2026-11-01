"""FastAPI inference service for AI-assisted complaint triage."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from ai_triage.train import predict as ml_predict
from ai_triage.fallback import predict as rule_predict

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
    priority_source: str = "ml"
    abstain_reason: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    text = f"{request.title} {request.description}"
    ml_result = ml_predict(request.title, request.description)
    rule_result = rule_predict(text)

    category = ml_result["category"]
    category_conf = ml_result.get("category_confidence")
    ml_priority = ml_result["priority"]
    ml_priority_conf = ml_result.get("priority_confidence")

    rule_priority = rule_result["priority"]
    rule_priority_conf = rule_result.get("priority_confidence")

    # Priority policy: trust rules when ML confidence is weak or signals conflict.
    use_ml_priority = (
        ml_priority_conf is not None
        and ml_priority_conf >= 0.6
        and (ml_priority == rule_priority or rule_priority_conf < 0.6)
    )

    if use_ml_priority:
        priority = ml_priority
        priority_conf = ml_priority_conf
        priority_source = "ml"
    else:
        priority = rule_priority
        priority_conf = rule_priority_conf
        priority_source = "rule"

    abstain = (category_conf is not None and category_conf < 0.5) or (
        priority_conf is not None and priority_conf < 0.5
    )
    abstain_reason = None
    if abstain:
        reasons = []
        if category_conf is not None and category_conf < 0.5:
            reasons.append(f"category_confidence={category_conf:.3f}")
        if priority_conf is not None and priority_conf < 0.5:
            reasons.append(f"priority_confidence={priority_conf:.3f}")
        abstain_reason = "; ".join(reasons)

    return TriageResponse(
        category=category,
        priority=priority,
        category_confidence=category_conf,
        priority_confidence=priority_conf,
        abstain=abstain,
        priority_source=priority_source,
        abstain_reason=abstain_reason,
    )
