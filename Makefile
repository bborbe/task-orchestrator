.PHONY: install format lint typecheck check test precommit run watch

# Development targets
install:
	uv sync --all-extras

format:
	uv run ruff format .
	uv run ruff check --fix . || true

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

check: lint typecheck

test:
	uv run pytest || test $$? -eq 5

precommit: format test check
	@echo "✓ All precommit checks passed"

# Run server
run:
	uv run task-orchestrator

# Run server with auto-reload on code changes
watch:
	uv run uvicorn task_orchestrator.__main__:app --reload --host 127.0.0.1 --port 8000
