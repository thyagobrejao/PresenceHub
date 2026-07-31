.PHONY: help install dev-install lint format typecheck test test-unit test-integration clean run run-dev docker-build docker-up docker-down db-init db-migrate

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

dev-install: ## Install development dependencies
	pip install -e ".[dev]"

lint: ## Run ruff linter
	ruff check .

format: ## Run ruff formatter
	ruff format .

typecheck: ## Run mypy type checker
	mypy .

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit -v

test-integration: ## Run integration tests only
	pytest tests/integration -v

test-cov: ## Run tests with coverage report
	pytest --cov=. --cov-report=term-missing --cov-report=html

clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

run: ## Run the application
	python -m api.server

run-dev: ## Run in development mode with hot reload
	uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

db-init: ## Initialize database (create tables)
	alembic upgrade head

db-migrate: ## Create a new migration (usage: make db-migrate MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services with Docker Compose
	docker compose up -d

docker-down: ## Stop all Docker Compose services
	docker compose down

docker-logs: ## View Docker Compose logs
	docker compose logs -f

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

all: lint typecheck test ## Run lint, typecheck, and tests
