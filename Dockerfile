# Multi-stage Dockerfile for Agent-Builder
FROM node:18-alpine AS frontend-builder

# Build frontend
WORKDIR /app/frontend
COPY builder/frontend/package*.json ./
RUN npm ci --only=production
COPY builder/frontend/ ./
RUN npm run build

# Python backend with built frontend
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements
COPY pyproject.toml ./
COPY builder/backend/requirements.txt ./builder/backend/

# Install Python dependencies
RUN pip install --no-cache-dir uv && \
    uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Copy backend code
COPY builder/backend/ ./builder/backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./builder/frontend/dist

# Copy configuration files
COPY builder/backend/.env.example ./builder/backend/.env
COPY builder/backend/servers_config.json ./builder/backend/
COPY builder/backend/enterprise_config.yaml ./builder/backend/

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=builder.backend.app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD [".venv/bin/python", "builder/backend/app.py"]