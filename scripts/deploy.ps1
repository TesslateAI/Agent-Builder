# =============================================================================
# Agent-Builder Deployment Script (PowerShell)
# Windows version of the deployment script
# =============================================================================

param(
    [string]$Environment = "dev",
    [string]$Command = "up",
    [string]$Service = ""
)

# Configuration
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

# Help function
function Show-Help {
    @"
Agent-Builder Deployment Script (PowerShell)

Usage: .\deploy.ps1 [-Environment <env>] [-Command <cmd>] [-Service <svc>]

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
    .\deploy.ps1 -Environment dev -Command up      # Start development environment
    .\deploy.ps1 -Environment prod -Command build  # Build production images
    .\deploy.ps1 -Environment dev -Command logs    # Show development logs
    .\deploy.ps1 -Environment prod -Command backup # Backup production data

"@
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    try {
        docker --version | Out-Null
    }
    catch {
        Write-Error "Docker is not installed or not in PATH"
        exit 1
    }
    
    # Check Docker Compose
    try {
        docker compose version | Out-Null
    }
    catch {
        Write-Error "Docker Compose is not available"
        exit 1
    }
    
    # Check environment file
    if ($Environment -eq "prod" -and -not (Test-Path "$ProjectRoot\.env.prod")) {
        Write-Error "Production environment file .env.prod not found"
        Write-Info "Copy .env.prod.example to .env.prod and configure it"
        exit 1
    }
    
    if ($Environment -eq "dev" -and -not (Test-Path "$ProjectRoot\.env")) {
        Write-Warning "Development environment file .env not found"
        Write-Info "Using default configuration"
    }
    
    Write-Success "Prerequisites check passed"
}

# Set environment-specific variables
function Initialize-Environment {
    if ($Environment -eq "prod") {
        $script:ComposeFile = "docker-compose.prod.yml"
        $script:EnvFile = ".env.prod"
        $script:ProjectName = "agent-builder-prod"
    } else {
        $script:ComposeFile = "docker-compose.dev.yml"
        $script:EnvFile = ".env"
        $script:ProjectName = "agent-builder-dev"
    }
    
    $env:COMPOSE_PROJECT_NAME = $script:ProjectName
    
    Write-Info "Environment: $Environment"
    Write-Info "Compose file: $script:ComposeFile"
}

# Build images
function Build-Images {
    Write-Info "Building images for $Environment environment..."
    
    if ($Command -eq "rebuild") {
        Write-Info "Rebuilding from scratch (no cache)..."
        docker compose -f $script:ComposeFile build --no-cache
    } else {
        docker compose -f $script:ComposeFile build
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Images built successfully"
    } else {
        Write-Error "Failed to build images"
        exit 1
    }
}

# Start services
function Start-Services {
    Write-Info "Starting $Environment services..."
    
    # Create necessary directories
    $DataDir = Join-Path $ProjectRoot "data"
    $LogsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force }
    if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir -Force }
    
    # Start services
    docker compose -f $script:ComposeFile up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services"
        exit 1
    }
    
    # Wait for health checks
    Write-Info "Waiting for services to be healthy..."
    Start-Sleep -Seconds 10
    
    # Show service status
    Show-Status
    
    Write-Success "$Environment environment started successfully"
    
    if ($Environment -eq "dev") {
        Write-Info "Development URLs:"
        Write-Info "  Frontend: http://localhost:5173"
        Write-Info "  Backend API: http://localhost:5000"
        Write-Info "  Traefik Dashboard: http://localhost:8080"
        Write-Info "  Redis Insight: http://localhost:8001"
        Write-Info "  PgAdmin: http://localhost:8002"
    } else {
        $domain = (Get-Content "$ProjectRoot\.env.prod" | Where-Object { $_ -match "^DOMAIN=" } | ForEach-Object { $_.Split("=")[1] })
        Write-Info "Production URLs:"
        Write-Info "  Application: https://$domain"
        Write-Info "  Monitoring: https://grafana.$domain"
    }
}

# Stop services
function Stop-Services {
    Write-Info "Stopping $Environment services..."
    docker compose -f $script:ComposeFile down
    Write-Success "Services stopped"
}

# Restart services
function Restart-Services {
    Write-Info "Restarting $Environment services..."
    docker compose -f $script:ComposeFile restart
    Write-Success "Services restarted"
}

# Show logs
function Show-Logs {
    if ($Service) {
        docker compose -f $script:ComposeFile logs -f $Service
    } else {
        docker compose -f $script:ComposeFile logs -f
    }
}

# Show status
function Show-Status {
    Write-Info "Service status:"
    docker compose -f $script:ComposeFile ps
    Write-Host ""
    Write-Info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}`t{{.CPUPerc}}`t{{.MemUsage}}`t{{.NetIO}}"
}

# Open shell
function Open-Shell {
    if ($Environment -eq "prod") {
        $containerName = "agent-builder-prod-app-1"
    } else {
        $containerName = "agent-builder-backend-dev"
    }
    
    Write-Info "Opening shell in $containerName..."
    docker exec -it $containerName /bin/bash
}

# Database migration
function Invoke-DbMigrate {
    if ($Environment -eq "prod") {
        $containerName = "agent-builder-prod-app-1"
    } else {
        $containerName = "agent-builder-backend-dev"
    }
    
    Write-Info "Running database migrations..."
    docker exec $containerName python -m alembic upgrade head
    Write-Success "Database migrations completed"
}

# Backup data (production only)
function Backup-Data {
    if ($Environment -ne "prod") {
        Write-Error "Backup is only available for production environment"
        exit 1
    }
    
    $backupDir = Join-Path $ProjectRoot "backups"
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir -Force
    }
    
    Write-Info "Creating backup..."
    
    # Database backup
    $dbBackupFile = Join-Path $backupDir "db_backup_$timestamp.sql"
    docker exec agent-builder-prod-postgres-1 pg_dump -U agentbuilder agentbuilder > $dbBackupFile
    
    # Application data backup
    $appBackupFile = Join-Path $backupDir "app_data_$timestamp.tar.gz"
    docker run --rm -v agent-builder-app-data:/data -v "${backupDir}:/backup" alpine tar czf "/backup/app_data_$timestamp.tar.gz" -C /data .
    
    Write-Success "Backup created: $backupDir/*_$timestamp.*"
}

# Main execution
function Main {
    Set-Location $ProjectRoot
    
    switch ($Command.ToLower()) {
        "help" { Show-Help; exit 0 }
        "up" {
            Test-Prerequisites
            Initialize-Environment
            Build-Images
            Start-Services
        }
        "down" {
            Initialize-Environment
            Stop-Services
        }
        "restart" {
            Initialize-Environment
            Restart-Services
        }
        "build" {
            Test-Prerequisites
            Initialize-Environment
            Build-Images
        }
        "rebuild" {
            Test-Prerequisites
            Initialize-Environment
            Build-Images
        }
        "logs" {
            Initialize-Environment
            Show-Logs
        }
        "status" {
            Initialize-Environment
            Show-Status
        }
        "shell" {
            Initialize-Environment
            Open-Shell
        }
        "db-migrate" {
            Initialize-Environment
            Invoke-DbMigrate
        }
        "backup" {
            Initialize-Environment
            Backup-Data
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Help
            exit 1
        }
    }
}

# Run main function
Main