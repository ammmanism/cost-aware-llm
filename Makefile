.PHONY: install test test-unit test-integration run lint format setup-git

install:
	pip install -e ".[dev]"

test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

run:
	uvicorn gateway.server:app --host 0.0.0.0 --port 8000 --reload

lint:
	ruff check .
	mypy .

format:
	black .
	isort .

setup-git:
	git init
	git add .
	git commit -m "feat: initial project structure"
	git checkout -b develop
	git checkout -b feature/providers
	git checkout -b feature/routing
	git checkout -b feature/caching
	git checkout -b feature/resiliency
	git checkout -b feature/multi-tenant
	git checkout -b feature/observability
	git checkout main

# Nexus-Standard: Verified Type Safety and Professional Documentation Pattern

