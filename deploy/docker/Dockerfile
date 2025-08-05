# =============================================================================
# Multi-stage Dockerfile for Agent-Builder
# Supports both development and production builds with best practices
# =============================================================================

# Build arguments for flexibility
ARG NODE_VERSION=18-alpine
ARG PYTHON_VERSION=3.11-slim
ARG BUILD_ENV=production

# =============================================================================
# Stage 1: Frontend Builder
# =============================================================================
FROM node:${NODE_VERSION} AS frontend-builder

# Set build environment
ARG BUILD_ENV
ENV NODE_ENV=${BUILD_ENV}

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Set working directory
WORKDIR /app/frontend

# Install dependencies first (better caching)
COPY builder/frontend/package*.json ./
RUN npm ci --only=production --silent

# Copy source code
COPY --chown=nextjs:nodejs builder/frontend/ ./

# Build frontend
RUN npm run build && \
    npm cache clean --force

# =============================================================================
# Stage 2: Python Dependencies
# =============================================================================
FROM python:${PYTHON_VERSION} AS python-deps

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install --no-cache-dir uv

# Create virtual environment
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Python requirements
COPY pyproject.toml ./
COPY builder/backend/requirements.txt ./builder/backend/

# Install Python dependencies including TFrameX and auth dependencies
RUN uv pip install --no-cache-dir flask flask-cors python-dotenv httpx pydantic PyYAML aiohttp beautifulsoup4 pandas tframex==1.1.0 PyJWT==2.8.0 redis==5.0.1 requests==2.32.3 SQLAlchemy==2.0.23 psycopg2-binary==2.9.9 alembic==1.13.1

# =============================================================================
# Stage 3: Production Runtime
# =============================================================================
FROM python:${PYTHON_VERSION} AS production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from dependencies stage
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend application
COPY --chown=appuser:appuser builder/backend/ ./builder/backend/

# Copy built frontend from builder stage
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./builder/frontend/dist

# Copy configuration files
COPY --chown=appuser:appuser builder/backend/.env.example ./builder/backend/.env.example
COPY --chown=appuser:appuser builder/backend/servers_config.json ./builder/backend/
COPY --chown=appuser:appuser builder/backend/enterprise_config.yaml ./builder/backend/

# Copy entrypoint script
COPY --chown=appuser:appuser scripts/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=builder.backend.app \
    PATH="/opt/venv/bin:$PATH"

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Run the application
CMD ["python", "builder/backend/app.py"]

# =============================================================================
# Stage 4: Development Runtime
# =============================================================================
FROM production AS development

# Switch back to root for development tools installation
USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install development Python dependencies
RUN /opt/venv/bin/pip install --no-cache-dir pytest black ruff mypy

# Create development directories
RUN mkdir -p /app/dev-data && \
    chown -R appuser:appuser /app

# Switch back to non-root user
USER appuser

# Development environment variables
ENV FLASK_ENV=development \
    FLASK_DEBUG=1

# Development health check (more frequent)
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=2 \
    CMD curl -f http://localhost:5000/health || exit 1

# Development command with auto-reload
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]