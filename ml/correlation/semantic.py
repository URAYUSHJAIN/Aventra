"""Semantic relevance between an anomaly description and news headlines (Sentence Transformers).

Optional component: if the embedding model cannot be loaded (no local cache and no
network), similarity is reported as unavailable instead of being guessed.
"""
from __future__ import annotations

import logging
from threading import Lock

from ml import config

logger = logging.getLogger(__name__)
_model = None
_failed = False
_lock = Lock()


def _load():
    global _model, _failed
    if _model is not None or _failed:
        return _model
    with _lock:
        if _model is None and not _failed:
            try:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(config.SEMANTIC_MODEL, device="cpu")
                logger.info("Semantic model loaded: %s", config.SEMANTIC_MODEL)
            except Exception:
                logger.warning("Semantic model %s unavailable; semantic relevance disabled", config.SEMANTIC_MODEL, exc_info=True)
                _failed = True
    return _model


def similarities(query: str, texts: list[str]) -> list[float] | None:
    """Cosine similarity of `query` to each text, or None when the model is unavailable."""
    if not texts:
        return []
    model = _load()
    if model is None:
        return None
    embeddings = model.encode([query, *texts], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return [round(float(value), 4) for value in embeddings[1:] @ embeddings[0]]


def model_info() -> dict:
    return {"model": config.SEMANTIC_MODEL, "status": "loaded" if _model is not None else ("unavailable" if _failed else "not_loaded")}
