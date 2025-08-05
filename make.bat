@echo off
setlocal enabledelayedexpansion

:: Agent-Builder Windows Make Script
:: Usage: make.bat [command]

set "PYTHON=python"
set "NPM=npm"
set "BACKEND_DIR=builder\backend"
set "FRONTEND_DIR=builder\frontend"
set "BACKEND_PORT=5000"
set "FRONTEND_PORT=5173"
set "DOCKER_DEV_COMPOSE=deploy\docker\docker-compose.dev.yml"
set "DOCKER_PROD_COMPOSE=deploy\docker\docker-compose.prod.yml"

:: Parse command
if "%1"=="" goto :help
goto :%1 2>nul || goto :invalid_command

:help
echo Agent-Builder Windows Build Script
echo.
echo Usage: make.bat [command]
echo.
echo Available commands:
echo   help                - Show this help message
echo   install             - Install all dependencies
echo   install-dev         - Install with development dependencies
echo   clean               - Clean build artifacts
echo   build               - Build frontend for production
echo   run                 - Run in production mode
echo   run-dev             - Run in development mode
echo   test                - Run tests
echo   lint                - Run linters
echo   format              - Format code
echo.
echo Docker Development:
echo   docker-dev-up       - Start development environment
echo   docker-dev-down     - Stop development environment
echo   docker-dev-restart  - Restart development environment
echo   docker-dev-logs     - Show development logs
echo   docker-dev-status   - Show container status
echo   docker-dev-clean    - Clean development containers
echo.
echo Docker Production:
echo   docker-prod-up      - Start production environment
echo   docker-prod-down    - Stop production environment
echo   docker-prod-logs    - Show production logs
goto :eof

:invalid_command
echo Error: Unknown command "%1"
echo Run "make.bat help" to see available commands
exit /b 1

:: Installation commands
:install
echo Installing dependencies...
call :setup_venv
echo Installing Python dependencies...
.venv\Scripts\pip install -e .
echo Installing frontend dependencies...
cd %FRONTEND_DIR%
call %NPM% install
echo Building frontend for production...
call %NPM% run build
cd ..\..
echo Installation complete!
goto :eof

:install-dev
echo Installing development dependencies...
call :setup_venv
echo Installing Python dependencies with dev extras...
.venv\Scripts\pip install -e ".[dev]"
echo Installing frontend dependencies...
cd %FRONTEND_DIR%
call %NPM% install
cd ..\..
echo Development installation complete!
goto :eof

:setup_venv
if not exist .venv (
    echo Creating Python virtual environment...
    %PYTHON% -m venv .venv
)
goto :eof

:: Clean command
:clean
echo Cleaning build artifacts...
if exist .venv rmdir /s /q .venv
if exist __pycache__ rmdir /s /q __pycache__
if exist builder.egg-info rmdir /s /q builder.egg-info
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
if exist %FRONTEND_DIR%\dist rmdir /s /q %FRONTEND_DIR%\dist
if exist %FRONTEND_DIR%\node_modules rmdir /s /q %FRONTEND_DIR%\node_modules
echo Clean complete!
goto :eof

:: Build command
:build
echo Building frontend...
cd %FRONTEND_DIR%
call %NPM% run build
cd ..\..
echo Build complete! Frontend built to %FRONTEND_DIR%\dist
goto :eof

:: Run commands
:run
echo Starting Agent-Builder in production mode...
call :activate_venv
cd %BACKEND_DIR%
%PYTHON% app.py
cd ..\..
goto :eof

:run-dev
echo Starting Agent-Builder in development mode...
start "Backend" cmd /c "call :run_backend_dev"
timeout /t 2 /nobreak >nul
start "Frontend" cmd /c "call :run_frontend_dev"
echo.
echo Development servers running!
echo   Backend API: http://localhost:%BACKEND_PORT%
echo   Frontend Dev: http://localhost:%FRONTEND_PORT%
echo.
echo Press Ctrl+C in each window to stop
goto :eof

:run_backend_dev
call :activate_venv
cd %BACKEND_DIR%
%PYTHON% app.py
goto :eof

:run_frontend_dev
cd %FRONTEND_DIR%
call %NPM% run dev
goto :eof

:activate_venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found. Run "make.bat install" first.
    exit /b 1
)
goto :eof

:: Test command
:test
echo Running backend tests...
call :activate_venv
cd %BACKEND_DIR%
%PYTHON% test_v1.1.0.py
cd ..\..
goto :eof

:: Lint command
:lint
echo Running Python linters...
call :activate_venv
ruff check builder\
echo Running frontend linters...
cd %FRONTEND_DIR%
call %NPM% run lint
cd ..\..
goto :eof

:: Format command
:format
echo Formatting Python code...
call :activate_venv
black builder\
ruff check --fix builder\
echo Code formatted!
goto :eof

:: Docker Development Commands
:docker-dev-up
echo Starting development environment...
docker-compose -f %DOCKER_DEV_COMPOSE% up -d
echo.
echo Development environment started!
echo   Frontend: http://localhost:5173
echo   Backend API: http://localhost:5000
echo   Keycloak: http://localhost:8081 (admin/admin)
echo   PgAdmin: http://localhost:8002 (admin@example.com/admin)
goto :eof

:docker-dev-down
echo Stopping development environment...
docker-compose -f %DOCKER_DEV_COMPOSE% down
goto :eof

:docker-dev-restart
echo Restarting development environment...
docker-compose -f %DOCKER_DEV_COMPOSE% down
docker-compose -f %DOCKER_DEV_COMPOSE% up -d
goto :eof

:docker-dev-logs
docker-compose -f %DOCKER_DEV_COMPOSE% logs -f
goto :eof

:docker-dev-status
docker-compose -f %DOCKER_DEV_COMPOSE% ps
goto :eof

:docker-dev-clean
echo Cleaning development containers and volumes...
docker-compose -f %DOCKER_DEV_COMPOSE% down -v --remove-orphans
echo Development environment cleaned!
goto :eof

:: Docker Production Commands
:docker-prod-up
echo Starting production environment...
docker-compose -f %DOCKER_PROD_COMPOSE% up -d
goto :eof

:docker-prod-down
echo Stopping production environment...
docker-compose -f %DOCKER_PROD_COMPOSE% down
goto :eof

:docker-prod-logs
docker-compose -f %DOCKER_PROD_COMPOSE% logs -f
goto :eof

endlocal