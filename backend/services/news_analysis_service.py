"""Adapter around the locally cloned FinBERT prediction implementation."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "finbert"


class FinBertUnavailable(RuntimeError):
    """The local FinBERT runtime or its model files are unavailable."""


class InvalidNewsText(ValueError):
    """The submitted text cannot be passed to FinBERT."""


class FinBertNewsAnalysisService:
    """Lazy singleton-friendly service that keeps the loaded FinBERT model in memory."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or os.getenv("FINBERT_MODEL_PATH", DEFAULT_MODEL_PATH))
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._load_lock = Lock()

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            if not (self.model_path / "config.json").is_file() or not (self.model_path / "pytorch_model.bin").is_file():
                logger.error("FinBERT model files are missing")
                raise FinBertUnavailable("FinBERT model files are missing.")
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path), local_files_only=True)
                self._model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path), local_files_only=True)
                self._model.eval()
                logger.info("FinBERT model loaded")
            except Exception as error:
                logger.exception("FinBERT model loading failed")
                raise FinBertUnavailable("FinBERT model could not be loaded.") from error

    def analyze(self, text: str) -> dict[str, float | str]:
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned:
            raise InvalidNewsText("News text is required.")
        self._load()
        try:
            import torch
            try:
                from nltk.tokenize import sent_tokenize
                sentences = sent_tokenize(cleaned)
            except LookupError:
                # NLTK's optional punkt data may not be provisioned in a
                # deployment. Preserve inference availability with a small,
                # deterministic sentence split rather than returning fake data.
                sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]
            if not sentences:
                raise InvalidNewsText("News text is required.")
            # FinBERT's original predictor uses 64-token sentence inputs and
            # returns classes in this order: positive, negative, neutral.
            inputs = self._tokenizer(sentences, padding=True, truncation=True, max_length=64, return_tensors="pt")
            with torch.no_grad():
                probabilities = torch.softmax(self._model(**inputs).logits, dim=-1).cpu().tolist()
            positive = sum(row[0] for row in probabilities) / len(probabilities)
            negative = sum(row[1] for row in probabilities) / len(probabilities)
            neutral = sum(row[2] for row in probabilities) / len(probabilities)
            label, _ = max((("positive", positive), ("negative", negative), ("neutral", neutral)), key=lambda item: item[1])
            return {
                "label": label,
                "positive_probability": round(float(positive), 6),
                "neutral_probability": round(float(neutral), 6),
                "negative_probability": round(float(negative), 6),
                "sentiment_score": round(float(positive - negative), 6),
            }
        except FinBertUnavailable:
            raise
        except Exception as error:
            logger.exception("FinBERT inference failed")
            raise FinBertUnavailable("FinBERT inference failed.") from error


_service: FinBertNewsAnalysisService | None = None
_service_lock = Lock()


def get_news_analysis_service() -> FinBertNewsAnalysisService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FinBertNewsAnalysisService()
    return _service
