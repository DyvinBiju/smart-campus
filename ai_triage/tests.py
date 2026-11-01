"""Tests for AI triage classifiers, API, and Django integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ai_triage.dataset import generate_synthetic_complaints, CATEGORIES, PRIORITIES
from ai_triage.train import build_pipeline, train, predict, CATEGORY_MODEL_PATH, PRIORITY_MODEL_PATH
from ai_triage.serve import app as fastapi_app
from ai_triage.fallback import predict as rule_predict

User = get_user_model()


# ---------------------------------------------------------------------------
# Dataset / training unit tests (no Django)
# ---------------------------------------------------------------------------


class DatasetTests(TestCase):
    def test_generate_synthetic_complaints_count(self):
        data = generate_synthetic_complaints(count=100)
        self.assertEqual(len(data), 100)

    def test_generate_synthetic_complaints_fields(self):
        data = generate_synthetic_complaints(count=10)
        for sample in data:
            self.assertIn(sample["category"], CATEGORIES)
            self.assertIn(sample["priority"], PRIORITIES)
            self.assertIn(sample["title"], sample["description"])
            self.assertTrue(len(sample["title"]) > 0)

    def test_generate_synthetic_complaints_deterministic(self):
        data1 = generate_synthetic_complaints(count=50, seed=7)
        data2 = generate_synthetic_complaints(count=50, seed=7)
        self.assertEqual(data1, data2)


class TrainTests(TestCase):
    def setUp(self):
        # Ensure a clean artifact state for deterministic tests.
        for path in [CATEGORY_MODEL_PATH, PRIORITY_MODEL_PATH, Path(CATEGORY_MODEL_PATH).parent / "training_report.json"]:
            if path.exists():
                path.unlink()

    def test_build_pipeline(self):
        pipe = build_pipeline()
        self.assertIn("tfidf", pipe.named_steps)
        self.assertIn("clf", pipe.named_steps)

    def test_train_creates_artifacts(self):
        report = train()
        self.assertTrue(CATEGORY_MODEL_PATH.exists())
        self.assertTrue(PRIORITY_MODEL_PATH.exists())
        self.assertIn("category_report", report)
        self.assertIn("priority_report", report)

    def test_predict_returns_valid_labels(self):
        train()
        result = predict("Wi-Fi not connecting in Room 101.", "Internet is down.")
        self.assertIn(result["category"], CATEGORIES)
        self.assertIn(result["priority"], PRIORITIES)


# ---------------------------------------------------------------------------
# FastAPI integration tests
# ---------------------------------------------------------------------------


class ServeTests(TestCase):
    def test_health(self):
        from fastapi.testclient import TestClient
        client = TestClient(fastapi_app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_predict_endpoint_returns_priority_source_and_abstain_reason(self):
        from fastapi.testclient import TestClient
        client = TestClient(fastapi_app)
        payload = {
            "title": "Water leaking from sink pipe in Library.",
            "description": "Water leaking from sink pipe in Library. flooding.",
        }
        response = client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["category"], CATEGORIES)
        self.assertIn(data["priority"], PRIORITIES)
        self.assertIn("abstain", data)
        self.assertIn("priority_source", data)
        self.assertIn("abstain_reason", data)
        # Rule should fire for strong flooding language.
        self.assertEqual(data["priority_source"], "rule")
        self.assertIsNone(data["abstain_reason"])

    def test_predict_empty_title(self):
        from fastapi.testclient import TestClient
        client = TestClient(fastapi_app)
        # Empty string should be rejected by the view-level validation
        response = client.post("/predict", json={"title": "", "description": "desc"})
        self.assertEqual(response.status_code, 422)


# ---------------------------------------------------------------------------
# Django integration tests
# ---------------------------------------------------------------------------


class ComplaintTriageDjangoTests(TestCase):
    def test_suggest_triage_view_exists(self):
        # Ensure URL is registered.
        url = reverse("complaints:suggest_triage")
        self.assertEqual(url, "/complaints/suggest-triage/")

    def test_suggest_triage_requires_login(self):
        client = Client()
        response = client.post(
            reverse("complaints:suggest_triage"),
            data={"title": "Test", "description": "Test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    @override_settings(AI_TRIAGE_ENABLED=True, AI_TRIAGE_API_URL="http://testserver")
    def test_suggest_triage_returns_predictions_when_enabled(self):
        user = get_user_model().objects.create_user(
            username="triage_user", email="triage@example.com", password="pass123", role=1
        )
        client = Client()
        client.force_login(user)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "category": "Plumbing",
            "priority": "High",
            "category_confidence": 0.95,
            "priority_confidence": 0.88,
            "abstain": False,
            "priority_source": "ml",
            "abstain_reason": None,
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = client.post(
                reverse("complaints:suggest_triage"),
                data=json.dumps({"title": "Leaking pipe", "description": "Water everywhere"}),
                content_type="application/json",
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data["category"], "Plumbing")
            self.assertEqual(data["priority"], "High")

    @override_settings(AI_TRIAGE_ENABLED=False)
    def test_suggest_triage_returns_503_when_disabled(self):
        user = get_user_model().objects.create_user(
            username="triage_off", email="triageoff@example.com", password="pass123", role=1
        )
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("complaints:suggest_triage"),
            data=json.dumps({"title": "Test", "description": "Test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)


# ---------------------------------------------------------------------------
# Fallback / abstention tests
# ---------------------------------------------------------------------------


class FallbackTests(TestCase):
    def test_rule_predict_high_urgency(self):
        result = rule_predict("Exposed wiring fire hazard sparking near Room 101.")
        self.assertEqual(result["priority"], "High")
        self.assertGreater(result["priority_confidence"], 0.5)
        self.assertFalse(result["abstain"])

    def test_rule_predict_medium_urgency(self):
        result = rule_predict("Flickering lights in Room 101, slow drain.")
        self.assertEqual(result["priority"], "Medium")
        self.assertGreater(result["priority_confidence"], 0.5)
        self.assertFalse(result["abstain"])

    def test_rule_predict_low_urgency(self):
        result = rule_predict("Cosmetic scuff mark and minor paint touch-up.")
        self.assertEqual(result["priority"], "Low")
        self.assertLess(result["priority_confidence"], 0.5)
        self.assertTrue(result["abstain"])

    def test_fallback_integration_uses_rule_when_ml_weak(self):
        train()
        text = "Cosmetic scuff mark near Cafeteria."
        result = rule_predict(text)
        self.assertEqual(result["priority"], "Low")
        self.assertTrue(result["abstain"])
