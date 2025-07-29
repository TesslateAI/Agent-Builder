# Agent-Builder Makefile
.PHONY: help install install-dev clean build run run-backend run-frontend test lint format setup-uv

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
UV := uv
NPM := npm
BACKEND_DIR := builder/backend
FRONTEND_DIR := builder/frontend
BACKEND_PORT := 5000
FRONTEND_PORT := 5173

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup-uv: ## Install uv package manager
	@command -v uv >/dev/null 2>&1 || { \
		echo "Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@echo "uv is installed"

install: setup-uv ## Install all dependencies (Python and Node)
	@echo "Creating Python virtual environment with uv..."
	$(UV) venv
	@echo "Installing Python dependencies..."
	@if [ -d "../TFrameX" ]; then \
		echo "Found local TFrameX, installing from ../TFrameX"; \
		$(UV) pip install -e ../TFrameX; \
		$(UV) pip install flask flask-cors python-dotenv httpx pydantic PyYAML aiohttp; \
	else \
		echo "Installing from pyproject.toml (requires TFrameX on PyPI)"; \
		$(UV) pip install -e .; \
	fi
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) install
	@echo "Building frontend for production..."
	cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "✅ Installation complete!"

install-dev: setup-uv ## Install all dependencies including dev tools
	@echo "Creating Python virtual environment with uv..."
	$(UV) venv
	@echo "Installing Python dependencies with dev extras..."
	@if [ -d "../TFrameX" ]; then \
		echo "Found local TFrameX, installing from ../TFrameX"; \
		$(UV) pip install -e ../TFrameX; \
		$(UV) pip install flask flask-cors python-dotenv httpx pydantic PyYAML aiohttp; \
		$(UV) pip install pytest pytest-asyncio black ruff mypy pre-commit; \
	else \
		$(UV) pip install -e ".[dev]"; \
	fi
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) install
	@echo "✅ Development installation complete!"

clean: ## Clean build artifacts and caches
	@echo "Cleaning Python artifacts..."
	rm -rf .venv
	rm -rf __pycache__
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleaning frontend artifacts..."
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/node_modules
	@echo "✅ Clean complete!"

build: ## Build the project for production
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "✅ Build complete! Frontend built to $(FRONTEND_DIR)/dist"

run: ## Run both backend and frontend in production mode
	@echo "Starting Agent-Builder in production mode..."
	@make run-backend &
	@sleep 2
	@echo ""
	@echo "✅ Agent-Builder is running!"
	@echo "   Backend API: http://localhost:$(BACKEND_PORT)"
	@echo "   Frontend: Served by Flask at http://localhost:$(BACKEND_PORT)"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@wait

run-backend: ## Run backend server (serves built frontend)
	@echo "Activating virtual environment and starting backend..."
	@. .venv/bin/activate && cd $(BACKEND_DIR) && $(PYTHON) app.py

run-frontend-dev: ## Run frontend in development mode (with hot reload)
	@echo "Starting frontend development server..."
	cd $(FRONTEND_DIR) && $(NPM) run dev

run-dev: ## Run in development mode (backend + frontend dev server)
	@echo "Starting Agent-Builder in development mode..."
	@make run-backend &
	@make run-frontend-dev &
	@echo ""
	@echo "✅ Development servers running!"
	@echo "   Backend API: http://localhost:$(BACKEND_PORT)"
	@echo "   Frontend Dev: http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@wait

test: ## Run tests
	@echo "Running backend tests..."
	@. .venv/bin/activate && cd $(BACKEND_DIR) && $(PYTHON) test_v1.1.0.py

lint: ## Run linters
	@echo "Running Python linters..."
	@. .venv/bin/activate && ruff check builder/
	@echo "Running frontend linters..."
	cd $(FRONTEND_DIR) && $(NPM) run lint || true

format: ## Format code
	@echo "Formatting Python code..."
	@. .venv/bin/activate && black builder/
	@. .venv/bin/activate && ruff check --fix builder/
	@echo "✅ Code formatted!"

docker-build: ## Build Docker image
	docker build -t agent-builder:latest .

docker-run: ## Run Docker container
	docker run -p $(BACKEND_PORT):$(BACKEND_PORT) \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-e OPENAI_API_BASE="$$OPENAI_API_BASE" \
		agent-builder:latest