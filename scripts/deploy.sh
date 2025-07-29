#!/bin/bash

# =============================================================================
# Agent-Builder Deployment Script
# Supports both development and production deployments
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"
COMMAND="${2:-up}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Agent-Builder Deployment Script

Usage: ./deploy.sh [ENVIRONMENT] [COMMAND]

ENVIRONMENTS:
    dev         Development environment with hot reload and debugging tools
    prod        Production environment with security and monitoring

COMMANDS:
    up          Start services (default)
    down        Stop services
    restart     Restart services
    build       Build images
    rebuild     Rebuild images from scratch
    logs        Show logs
    status      Show service status
    shell       Open shell in app container
    db-migrate  Run database migrations
    backup      Backup data (production only)
    restore     Restore data (production only)

Examples:
    ./deploy.sh dev up          # Start development environment
    ./deploy.sh prod build      # Build production images
    ./deploy.sh dev logs        # Show development logs
    ./deploy.sh prod backup     # Backup production data

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        exit 1
    fi
    
    # Check environment file
    if [[ "$ENVIRONMENT" == "prod" ]] && [[ ! -f "$PROJECT_ROOT/.env.prod" ]]; then
        log_error "Production environment file .env.prod not found"
        log_info "Copy .env.prod.example to .env.prod and configure it"
        exit 1
    fi
    
    if [[ "$ENVIRONMENT" == "dev" ]] && [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        log_warning "Development environment file .env not found"
        log_info "Using default configuration"
    fi
    
    log_success "Prerequisites check passed"
}

# Set environment-specific variables
setup_environment() {
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        ENV_FILE=".env.prod"
        PROJECT_NAME="agent-builder-prod"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
        ENV_FILE=".env"
        PROJECT_NAME="agent-builder-dev"
    fi
    
    export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
    
    log_info "Environment: $ENVIRONMENT"
    log_info "Compose file: $COMPOSE_FILE"
}

# Build images
build_images() {
    log_info "Building images for $ENVIRONMENT environment..."
    
    if [[ "$COMMAND" == "rebuild" ]]; then
        log_info "Rebuilding from scratch (no cache)..."
        docker compose -f "$COMPOSE_FILE" build --no-cache
    else
        docker compose -f "$COMPOSE_FILE" build
    fi
    
    log_success "Images built successfully"
}

# Start services
start_services() {
    log_info "Starting $ENVIRONMENT services..."
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs"
    
    # Start services
    docker compose -f "$COMPOSE_FILE" up -d
    
    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Show service status
    show_status
    
    log_success "$ENVIRONMENT environment started successfully"
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        log_info "Development URLs:"
        log_info "  Frontend: http://localhost:5173"
        log_info "  Backend API: http://localhost:5000"
        log_info "  Traefik Dashboard: http://localhost:8080"
        log_info "  Redis Insight: http://localhost:8001"
        log_info "  PgAdmin: http://localhost:8002"
    else
        log_info "Production URLs:"
        log_info "  Application: https://$(grep DOMAIN .env.prod | cut -d'=' -f2)"
        log_info "  Monitoring: https://grafana.$(grep DOMAIN .env.prod | cut -d'=' -f2)"
    fi
}

# Stop services
stop_services() {
    log_info "Stopping $ENVIRONMENT services..."
    docker compose -f "$COMPOSE_FILE" down
    log_success "Services stopped"
}

# Restart services
restart_services() {
    log_info "Restarting $ENVIRONMENT services..."
    docker compose -f "$COMPOSE_FILE" restart
    log_success "Services restarted"
}

# Show logs
show_logs() {
    local service="${3:-}"
    if [[ -n "$service" ]]; then
        docker compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Show status
show_status() {
    log_info "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo
    log_info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Open shell
open_shell() {
    local container_name
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        container_name="agent-builder-prod-app-1"
    else
        container_name="agent-builder-backend-dev"
    fi
    
    log_info "Opening shell in $container_name..."
    docker exec -it "$container_name" /bin/bash
}

# Database migration
db_migrate() {
    local container_name
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        container_name="agent-builder-prod-app-1"
    else
        container_name="agent-builder-backend-dev"
    fi
    
    log_info "Running database migrations..."
    docker exec "$container_name" python -m alembic upgrade head
    log_success "Database migrations completed"
}

# Backup data (production only)
backup_data() {
    if [[ "$ENVIRONMENT" != "prod" ]]; then
        log_error "Backup is only available for production environment"
        exit 1
    fi
    
    local backup_dir="$PROJECT_ROOT/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p "$backup_dir"
    
    log_info "Creating backup..."
    
    # Database backup
    docker exec agent-builder-prod-postgres-1 pg_dump -U agentbuilder agentbuilder > "$backup_dir/db_backup_$timestamp.sql"
    
    # Application data backup
    docker run --rm -v agent-builder-app-data:/data -v "$backup_dir":/backup alpine tar czf "/backup/app_data_$timestamp.tar.gz" -C /data .
    
    log_success "Backup created: $backup_dir/*_$timestamp.*"
}

# Restore data (production only)
restore_data() {
    if [[ "$ENVIRONMENT" != "prod" ]]; then
        log_error "Restore is only available for production environment"
        exit 1
    fi
    
    local backup_file="${3:-}"
    if [[ -z "$backup_file" ]]; then
        log_error "Please specify backup file: ./deploy.sh prod restore <backup_file>"
        exit 1
    fi
    
    log_warning "This will overwrite existing data. Are you sure? (y/N)"
    read -r response
    if [[ "$response" != "y" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    log_info "Restoring from backup: $backup_file"
    
    # Restore database
    if [[ "$backup_file" == *.sql ]]; then
        docker exec -i agent-builder-prod-postgres-1 psql -U agentbuilder agentbuilder < "$backup_file"
    fi
    
    log_success "Restore completed"
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    case "$COMMAND" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "up")
            check_prerequisites
            setup_environment
            build_images
            start_services
            ;;
        "down")
            setup_environment
            stop_services
            ;;
        "restart")
            setup_environment
            restart_services
            ;;
        "build")
            check_prerequisites
            setup_environment
            build_images
            ;;
        "rebuild")
            check_prerequisites
            setup_environment
            build_images
            ;;
        "logs")
            setup_environment
            show_logs "$@"
            ;;
        "status")
            setup_environment
            show_status
            ;;
        "shell")
            setup_environment
            open_shell
            ;;
        "db-migrate")
            setup_environment
            db_migrate
            ;;
        "backup")
            setup_environment
            backup_data
            ;;
        "restore")
            setup_environment
            restore_data "$@"
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"