FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system rupturelab \
    && useradd --system --gid rupturelab --home-dir /nonexistent rupturelab

COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN python -m pip install --no-cache-dir .

USER rupturelab

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "rupturelab.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
