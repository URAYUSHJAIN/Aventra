# Aventra backend: Flask API + ML pipeline (FinBERT, detectors, correlation) in one container.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# CPU-only PyTorch keeps the image far smaller than the default CUDA build.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<2.5" \
 && pip install -r backend/requirements.txt

COPY ml ml
COPY backend backend
COPY scripts scripts
COPY data/reference data/reference
COPY data/demo data/demo

RUN useradd --create-home aventra && mkdir -p /app/state && chown -R aventra /app
USER aventra

# Mutable state (SQLite, trained artefacts, Hugging Face cache) lives on the /app/state volume.
# FinBERT weights are mounted read-only at /models/finbert (see docker-compose.yml); they are not baked into the image.
ENV AVENTRA_DB_PATH=/app/state/aventra.sqlite3 \
    AVENTRA_ARTIFACT_DIR=/app/state/artifacts \
    HF_HOME=/app/state/huggingface \
    FINBERT_MODEL_PATH=/models/finbert

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4).status == 200 else 1)"

# One worker keeps a single copy of the models in memory; threads serve concurrent requests.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "180", "backend.app:create_app()"]
