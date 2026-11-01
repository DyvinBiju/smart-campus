"""Train TF-IDF + Logistic Regression classifiers for category and priority prediction."""

from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from ai_triage.dataset import generate_synthetic_complaints, CATEGORIES, PRIORITIES

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
CATEGORY_MODEL_PATH = ARTIFACTS_DIR / "category_model.joblib"
PRIORITY_MODEL_PATH = ARTIFACTS_DIR / "priority_model.joblib"
REPORT_PATH = ARTIFACTS_DIR / "training_report.json"


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.95,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def _to_serialisable_report(report_dict: dict, labels: list[str]) -> dict:
    """Convert sklearn report dict to a JSON-safe structure with confusion matrix."""
    return {
        "labels": labels,
        "per_class": {
            label: {
                "precision": float(report_dict[label]["precision"]),
                "recall": float(report_dict[label]["recall"]),
                "f1_score": float(report_dict[label]["f1-score"]),
                "support": int(report_dict[label]["support"]),
            }
            for label in labels
        },
        "accuracy": float(report_dict["accuracy"]),
        "macro_avg": {
            "precision": float(report_dict["macro avg"]["precision"]),
            "recall": float(report_dict["macro avg"]["recall"]),
            "f1_score": float(report_dict["macro avg"]["f1-score"]),
        },
        "weighted_avg": {
            "precision": float(report_dict["weighted avg"]["precision"]),
            "recall": float(report_dict["weighted avg"]["recall"]),
            "f1_score": float(report_dict["weighted avg"]["f1-score"]),
        },
    }


def train() -> dict:
    data = generate_synthetic_complaints(count=600)
    texts = [f"{sample['title']} {sample['description']}" for sample in data]
    category_labels = [sample["category"] for sample in data]
    priority_labels = [sample["priority"] for sample in data]

    X_train, X_test, y_cat_train, y_cat_test = train_test_split(
        texts, category_labels, test_size=0.2, random_state=42, stratify=category_labels
    )
    _, _, y_pri_train, y_pri_test = train_test_split(
        texts, priority_labels, test_size=0.2, random_state=42, stratify=priority_labels
    )

    category_model = build_pipeline()
    category_model.fit(X_train, y_cat_train)
    category_preds = category_model.predict(X_test)
    category_report = classification_report(
        y_cat_test, category_preds, output_dict=True, zero_division=0
    )
    category_cm = confusion_matrix(y_cat_test, category_preds, labels=CATEGORIES).tolist()

    priority_model = build_pipeline()
    priority_model.fit(X_train, y_pri_train)
    priority_preds = priority_model.predict(X_test)
    priority_report = classification_report(
        y_pri_test, priority_preds, output_dict=True, zero_division=0
    )
    priority_cm = confusion_matrix(y_pri_test, priority_preds, labels=PRIORITIES).tolist()

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(category_model, CATEGORY_MODEL_PATH)
    joblib.dump(priority_model, PRIORITY_MODEL_PATH)

    report = {
        "samples_total": len(data),
        "category_report": _to_serialisable_report(category_report, CATEGORIES),
        "category_confusion_matrix": {
            "labels": CATEGORIES,
            "matrix": category_cm,
        },
        "priority_report": _to_serialisable_report(priority_report, PRIORITIES),
        "priority_confusion_matrix": {
            "labels": PRIORITIES,
            "matrix": priority_cm,
        },
        "category_model_path": str(CATEGORY_MODEL_PATH),
        "priority_model_path": str(PRIORITY_MODEL_PATH),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))

    return report


def load_models() -> tuple[Pipeline, Pipeline]:
    if not CATEGORY_MODEL_PATH.exists() or not PRIORITY_MODEL_PATH.exists():
        raise FileNotFoundError("Model artifacts missing. Run training first.")
    return joblib.load(CATEGORY_MODEL_PATH), joblib.load(PRIORITY_MODEL_PATH)


def predict(title: str, description: str) -> dict:
    category_model, priority_model = load_models()
    text = f"{title} {description}"
    category = category_model.predict([text])[0]
    priority = priority_model.predict([text])[0]
    try:
        category_conf = float(max(category_model.predict_proba([text])[0]))
        priority_conf = float(max(priority_model.predict_proba([text])[0]))
    except Exception:
        category_conf = None
        priority_conf = None
    return {
        "category": category,
        "priority": priority,
        "category_confidence": category_conf,
        "priority_confidence": priority_conf,
    }


if __name__ == "__main__":
    report = train()
    print(json.dumps(report, indent=2))
