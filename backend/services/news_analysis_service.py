"""Backward-compatible import path for the FinBERT service.

The implementation moved to `ml.news.finbert` (the ML package owns model logic);
existing imports of these names from this module keep working.
"""
from ml.news.finbert import (  # noqa: F401
    DEFAULT_MODEL_PATH,
    FinBertNewsAnalysisService,
    FinBertUnavailable,
    InvalidNewsText,
    get_news_analysis_service,
)
