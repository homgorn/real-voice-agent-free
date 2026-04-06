.PHONY: install test lint format run worker docker-build docker-up docker-down clean migrate migrate-autogen audit

install:
	uv sync --frozen
	uv run pre-commit install

sync:
	uv sync --frozen

update:
	uv lock --upgrade

test:
	uv run pytest tests/ -v --tb=short

lint:
	uv run ruff check apps/api/src/
	uv run ruff format --check apps/api/src/

format:
	uv run ruff check apps/api/src/ --fix
	uv run ruff format apps/api/src/

run:
	uv run uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

worker:
	uv run python -m voiceagent_api.worker

docker-build:
	docker build -t voiceagent:latest .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api worker

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/

migrate:
	uv run alembic upgrade head

migrate-autogen:
	uv run alembic revision --autogenerate -m "$(message)"

audit:
	uv run pip-audit
