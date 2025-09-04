# GARD Chatbot Makefile
.PHONY: help install install-dev test lint format clean run docker-build docker-run

help: ## Show this help message
	@echo "GARD Chatbot - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8 mypy pre-commit
	pre-commit install

test: ## Run tests
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests only
	pytest tests/ -v -m integration

lint: ## Run linting
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	mypy . --ignore-missing-imports

format: ## Format code
	black .
	isort .

format-check: ## Check code formatting
	black --check .
	isort --check-only .

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

run: ## Run the application
	streamlit run gard_chatbot_app_V2-2.py

run-dev: ## Run the application in development mode
	DEBUG_MODE=true streamlit run gard_chatbot_app_V2-2.py

docker-build: ## Build Docker image
	docker build -t gard-chatbot:latest .

docker-run: ## Run Docker container
	docker run -p 8501:8501 --env-file .env gard-chatbot:latest

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

security-check: ## Run security checks
	safety check
	bandit -r . -f json -o bandit-report.json

setup: install-dev ## Initial setup for development
	@echo "Setting up GARD Chatbot development environment..."
	@echo "Please copy env.example to .env and configure your environment variables"
	@echo "Run 'make run' to start the application"

ci: lint test security-check ## Run all CI checks

all: clean install-dev test lint format ## Run all checks and formatting
