FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY alembic.ini ./
COPY alembic ./alembic
COPY contracts ./contracts
COPY docs ./docs
COPY prd ./prd
COPY backlog ./backlog

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000"]
