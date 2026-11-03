.PHONY: dev test lint eval api worker db-up db-down migrate grobid clean web

dev:
	uv sync --all-extras

test:
	uv run pytest tests/unit tests/integration tests/contract -v

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

eval:
	uv run pytest tests/eval -v -s

api:
	uv run uvicorn prismai.api.main:app --reload --port 8000

worker:
	uv run saq prismai.queue.settings.saq_settings --verbose

db-up:
	docker compose up -d postgres
	@echo "Waiting for Postgres..."
	@sleep 2
	uv run alembic upgrade head

db-down:
	docker compose down -v

migrate:
	uv run alembic upgrade head

grobid:
	docker compose up -d grobid

web:
	cd ../prismai-web && npm run dev

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache
