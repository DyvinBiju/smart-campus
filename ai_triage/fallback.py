"""Rule-based fallback triage for priority prediction.

This module provides a lightweight, interpretable priority classifier that
complements the ML model. It is used when:
- ML priority confidence is below the abstention threshold.
- ML and rule-based predictions disagree (ML is not trusted on priority
  because the synthetic dataset still does not match real campus language).
"""

from __future__ import annotations

_HIGH_PATTERNS = [
    "emergency",
    "urgent",
    "urgently",
    "immediate",
    "flooding",
    "fire",
    "sparking",
    "shock",
    "exposed wiring",
    "power outage",
    "no water",
    "sewage",
    "biohazard",
    "infestation",
    "unsafe",
    "hazard",
    "blocked",
    "crashing",
    "unreachable",
    "server down",
    "outage",
    "data loss",
    "security breach",
    "burst pipe",
    "leaking",
]

_MEDIUM_PATTERNS = [
    "flickering",
    "low pressure",
    "stuck",
    "loose",
    "sticky",
    "offline",
    "distorted",
    "missing",
    "foul smell",
    "overdue",
    "slow",
    "noisy",
    "soon",
    "needs",
    "intermittent",
    "wobbly",
    "dripping",
    "clogged",
    "dim",
    "lag",
]


def _score(text: str) -> tuple[str, float, str]:
    """Return (priority, confidence, reason) for a complaint text."""
    lowered = text.lower()
    high_hits = [p for p in _HIGH_PATTERNS if p in lowered]
    medium_hits = [p for p in _MEDIUM_PATTERNS if p in lowered]

    if high_hits and not medium_hits:
        return "High", 0.85, f"matched:{high_hits[0]}"
    if medium_hits and not high_hits:
        return "Medium", 0.7, f"matched:{medium_hits[0]}"
    if high_hits and medium_hits:
        return "High", 0.75, "high_and_medium_signals"
    return "Low", 0.4, "no_urgency_signal"


def predict(text: str) -> dict:
    """Predict priority using rule-based heuristics."""
    priority, confidence, reason = _score(text)
    return {
        "priority": priority,
        "priority_confidence": confidence,
        "priority_reason": reason,
        "abstain": confidence < 0.5,
    }
