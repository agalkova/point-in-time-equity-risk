FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OUTPUT_ROOT=/app/output

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install ".[cloud]"

COPY configs ./configs
COPY data/example ./data/example
COPY scripts/run_example_pipeline.py scripts/run_cloud_synthetic_job.py ./scripts/

RUN mkdir -p /app/output && chown -R app:app /app
USER app

ENTRYPOINT ["python", "scripts/run_cloud_synthetic_job.py"]
