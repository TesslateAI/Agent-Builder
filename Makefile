# Agent-Builder Makefile
.PHONY: help install install-dev clean build run run-backend run-frontend test lint format setup-uv \
        docker-dev-up docker-dev-down docker-dev-build docker-dev-logs docker-dev-shell \
        docker-prod-up docker-prod-down docker-prod-build docker-prod-deploy docker-prod-backup \
        docker-clean docker-prune

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
	$(UV) pip install -e .
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) install
	@echo "Building frontend for production..."
	cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "✅ Installation complete!"

install-dev: setup-uv ## Install all dependencies including dev tools
	@echo "Creating Python virtual environment with uv..."
	$(UV) venv
	@echo "Installing Python dependencies with dev extras..."
	$(UV) pip install -e ".[dev]"
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

# =============================================================================
# Docker Development Commands
# =============================================================================

docker-dev-up: ## Start development environment with Docker
	@echo "Starting development environment..."
	@./deploy/scripts/deploy.sh dev up

docker-dev-down: ## Stop development environment
	@echo "Stopping development environment..."
	@./deploy/scripts/deploy.sh dev down

docker-dev-build: ## Build development images
	@echo "Building development images..."
	@./deploy/scripts/deploy.sh dev build

docker-dev-rebuild: ## Rebuild development images from scratch
	@echo "Rebuilding development images..."
	@./deploy/scripts/deploy.sh dev rebuild

docker-dev-logs: ## Show development logs
	@./deploy/scripts/deploy.sh dev logs

docker-dev-status: ## Show development service status
	@./deploy/scripts/deploy.sh dev status

docker-dev-shell: ## Open shell in development backend container
	@./deploy/scripts/deploy.sh dev shell

docker-dev-restart: ## Restart development services
	@./deploy/scripts/deploy.sh dev restart

# =============================================================================
# Docker Production Commands
# =============================================================================

docker-prod-up: ## Start production environment with Docker
	@echo "Starting production environment..."
	@./deploy/scripts/deploy.sh prod up

docker-prod-down: ## Stop production environment
	@echo "Stopping production environment..."
	@./deploy/scripts/deploy.sh prod down

docker-prod-build: ## Build production images
	@echo "Building production images..."
	@./deploy/scripts/deploy.sh prod build

docker-prod-rebuild: ## Rebuild production images from scratch
	@echo "Rebuilding production images..."
	@./deploy/scripts/deploy.sh prod rebuild

docker-prod-deploy: ## Deploy to production (build + up)
	@echo "Deploying to production..."
	@./deploy/scripts/deploy.sh prod build && ./deploy/scripts/deploy.sh prod up

docker-prod-logs: ## Show production logs
	@./deploy/scripts/deploy.sh prod logs

docker-prod-status: ## Show production service status
	@./deploy/scripts/deploy.sh prod status

docker-prod-shell: ## Open shell in production app container
	@./deploy/scripts/deploy.sh prod shell

docker-prod-backup: ## Backup production data
	@./deploy/scripts/deploy.sh prod backup

docker-prod-restart: ## Restart production services
	@./deploy/scripts/deploy.sh prod restart

# =============================================================================
# Docker Maintenance Commands
# =============================================================================

docker-clean: ## Clean up Docker resources
	@echo "Cleaning up Docker resources..."
	@docker compose -f deploy/docker/docker-compose.dev.yml down --remove-orphans --volumes || true
	@docker compose -f deploy/docker/docker-compose.prod.yml down --remove-orphans --volumes || true
	@docker system prune -f

docker-prune: ## Aggressive Docker cleanup (removes all unused resources)
	@echo "Performing aggressive Docker cleanup..."
	@docker system prune -af --volumes
	@docker volume prune -f
	@docker network prune -f

docker-logs-backend: ## Show backend logs only (dev)
	@docker compose -f deploy/docker/docker-compose.dev.yml logs -f backend

docker-logs-frontend: ## Show frontend logs only (dev)
	@docker compose -f deploy/docker/docker-compose.dev.yml logs -f frontend

# =============================================================================
# Legacy Docker Commands (for backward compatibility)
# =============================================================================

docker-build: ## Build Docker image (legacy - use docker-dev-build or docker-prod-build)
	@echo "⚠️  Legacy command. Use 'make docker-dev-build' or 'make docker-prod-build'"
	@docker build -f deploy/docker/Dockerfile --target production -t agent-builder:latest .

docker-run: ## Run Docker container (legacy - use docker-dev-up or docker-prod-up)
	@echo "⚠️  Legacy command. Use 'make docker-dev-up' or 'make docker-prod-up'"
	@docker run -p $(BACKEND_PORT):$(BACKEND_PORT) \
		-e OPENAI_API_KEY="$$OPENAI_API_KEY" \
		-e OPENAI_API_BASE="$$OPENAI_API_BASE" \
		agent-builder:latest