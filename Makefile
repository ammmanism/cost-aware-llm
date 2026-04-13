.PHONY: install test run lint setup-git

install:
	pip install -e ".[dev]"

test:
	pytest tests/

run:
	uvicorn gateway.server:app --host 0.0.0.0 --port 8000 --reload

lint:
	black .
	isort .
	mypy .

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
