"""FinBERT financial-sentiment inference (moved from backend/services/news_analysis_service.py).

The inference behaviour of the original service is unchanged: sentences are
classified with 64-token inputs and class probabilities are averaged across
sentences. `analyze_many` batches several documents for news ingestion.
FinBERT is a sentiment model only — not fake-news, fraud or manipulation detection.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

from ml import config

logger = logging.getLogger(__name__)
DEFAULT_MODEL_PATH = config.PROJECT_ROOT / "backend" / "models" / "finbert"
MODEL_NAME = "ProsusAI/finBERT"
MAX_SENTENCE_TOKENS = 64
BATCH_SIZE = 32


class FinBertUnavailable(RuntimeError):
    """The local FinBERT runtime or its model files are unavailable."""


class InvalidNewsText(ValueError):
    """The submitted text cannot be passed to FinBERT."""


def _split_sentences(text: str) -> list[str]:
    try:
        from nltk.tokenize import sent_tokenize
        return sent_tokenize(text)
    except LookupError:
        # NLTK's optional punkt data may not be provisioned in a deployment. Preserve
        # inference availability with a deterministic split rather than returning fake data.
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


class FinBertNewsAnalysisService:
    """Lazy singleton-friendly service that keeps the loaded FinBERT model in memory."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or os.getenv("FINBERT_MODEL_PATH", DEFAULT_MODEL_PATH))
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._load_lock = Lock()
        self.model_version: str | None = None

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
                self.model_version = "config-sha1:" + hashlib.sha1((self.model_path / "config.json").read_bytes()).hexdigest()[:12]
                logger.info("FinBERT model loaded")
            except Exception as error:
                logger.exception("FinBERT model loading failed")
                raise FinBertUnavailable("FinBERT model could not be loaded.") from error

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except FinBertUnavailable:
            return False

    def _probabilities(self, sentences: list[str]) -> list[list[float]]:
        import torch
        rows: list[list[float]] = []
        for start in range(0, len(sentences), BATCH_SIZE):
            inputs = self._tokenizer(sentences[start:start + BATCH_SIZE], padding=True, truncation=True, max_length=MAX_SENTENCE_TOKENS, return_tensors="pt")
            with torch.no_grad():
                rows.extend(torch.softmax(self._model(**inputs).logits, dim=-1).cpu().tolist())
        return rows

    def _summarise(self, probabilities: list[list[float]]) -> dict[str, float | str]:
        # FinBERT's original predictor returns classes in this order: positive, negative, neutral.
        positive = sum(row[0] for row in probabilities) / len(probabilities)
        negative = sum(row[1] for row in probabilities) / len(probabilities)
        neutral = sum(row[2] for row in probabilities) / len(probabilities)
        label, confidence = max((("positive", positive), ("negative", negative), ("neutral", neutral)), key=lambda item: item[1])
        return {
            "label": label,
            "positive_probability": round(float(positive), 6),
            "neutral_probability": round(float(neutral), 6),
            "negative_probability": round(float(negative), 6),
            "sentiment_score": round(float(positive - negative), 6),
            # Mean softmax probability of the winning class; softmax outputs are not calibrated probabilities.
            "confidence": round(float(confidence), 6),
            "model": MODEL_NAME,
            "model_version": self.model_version,
        }

    def analyze(self, text: str) -> dict[str, float | str]:
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned:
            raise InvalidNewsText("News text is required.")
        self._load()
        try:
            sentences = _split_sentences(cleaned)
            if not sentences:
                raise InvalidNewsText("News text is required.")
            return self._summarise(self._probabilities(sentences))
        except (FinBertUnavailable, InvalidNewsText):
            raise
        except Exception as error:
            logger.exception("FinBERT inference failed")
            raise FinBertUnavailable("FinBERT inference failed.") from error

    def analyze_many(self, texts: list[str]) -> list[dict[str, float | str] | None]:
        """Batch inference for many short documents (e.g. headlines). Empty texts yield None."""
        self._load()
        spans, sentences = [], []
        for text in texts:
            parts = _split_sentences(text.strip()) if isinstance(text, str) and text.strip() else []
            spans.append((len(sentences), len(sentences) + len(parts)))
            sentences.extend(parts)
        try:
            probabilities = self._probabilities(sentences) if sentences else []
        except Exception as error:
            logger.exception("FinBERT batch inference failed")
            raise FinBertUnavailable("FinBERT inference failed.") from error
        return [self._summarise(probabilities[start:end]) if end > start else None for start, end in spans]


_service: FinBertNewsAnalysisService | None = None
_service_lock = Lock()


def get_news_analysis_service() -> FinBertNewsAnalysisService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FinBertNewsAnalysisService()
    return _service
