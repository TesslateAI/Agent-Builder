# Docker Setup for Agent-Builder

## Overview

The Agent-Builder now has a comprehensive Docker setup supporting both development and production environments with best practices for security, scalability, and maintainability.

## Quick Start

### Development Environment
```bash
# Start development environment (recommended)
docker-compose -f docker-compose.dev.yml up -d

# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Production Environment
```bash
# Create production environment file
cp .env.prod.example .env.prod
# Edit .env.prod with your actual values

# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Check status  
docker-compose -f docker-compose.prod.yml ps

# Stop
docker-compose -f docker-compose.prod.yml down
```

## Architecture

### Multi-Stage Dockerfile
- **Frontend Builder**: Builds React app with Vite
- **Python Dependencies**: Installs Python packages with uv for speed
- **Production**: Minimal runtime image with security hardening
- **Development**: Extended with dev tools and hot reload

### Services

#### Development Environment (`docker-compose.dev.yml`)
- **Backend**: Flask API with TFrameX, hot reload enabled (uses SQLite by default)
- **Frontend**: Vite dev server with hot reload
- **PostgreSQL**: Optional database for enterprise features
- **Redis**: Caching layer
- **Ollama**: Local LLM server
- **Traefik**: Reverse proxy and load balancer
- **PgAdmin**: Database administration
- **RedisInsight**: Redis administration

#### Production Environment (`docker-compose.prod.yml`)
- **App**: Combined Flask + built React (uses SQLite by default)
- **PostgreSQL**: Optional database for enterprise features
- **Redis**: Caching layer with authentication
- **Traefik**: SSL termination and load balancing

## Configuration

### Environment Variables

**Development** (`.env`):
```bash
OPENAI_API_KEY=your_key_here
OPENAI_API_BASE=http://localhost:11434/v1  # For Ollama
OPENAI_MODEL_NAME=llama3
FLASK_ENV=development
FLASK_DEBUG=1
```

**Production** (`.env.prod`):
```bash
# Database
POSTGRES_USER=agentbuilder_prod
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=agentbuilder_production

# Security
REDIS_PASSWORD=secure_redis_password
ACME_EMAIL=admin@yourdomain.com
TRAEFIK_AUTH=admin:$apr1$hash$here

# LLM
OPENAI_API_KEY=your_production_key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4
```

### TFrameX Integration

The Docker setup automatically handles TFrameX installation:
- **Package Installation**: TFrameX v1.1.0 is installed via pip during image build
- **Clean Setup**: No volume mounts or complex installation scripts needed
- **Fast Startup**: Pre-installed package means instant container startup

### Database Architecture

The application uses a flexible database approach:
- **Default**: SQLite for simple, file-based storage (no setup required)
- **Enterprise**: PostgreSQL containers available for advanced features
- **Configuration**: Switch between databases via environment variables

## Best Practices

### Security
- Non-root user execution
- Minimal base images (Alpine/slim)
- Security opts (no-new-privileges)
- Environment-specific credentials
- SSL/TLS termination in production

### Performance
- Multi-stage builds for smaller images
- Layer caching optimization
- Resource limits and reservations
- Health checks for all services
- Dependency-based startup ordering

### Development Workflow
- Hot reload for both frontend and backend
- Volume mounts for source code
- Separate networks for isolation
- Comprehensive logging
- Database and cache administration tools

## Management & Administration

### Development
- **Traefik Dashboard**: http://localhost:8080
- **PgAdmin**: http://localhost:5050
- **RedisInsight**: http://localhost:8001
- **Ollama**: http://localhost:11434

### Production
- **Traefik Dashboard**: https://traefik.yourdomain.com (secured)

## Maintenance

### Cleanup
```bash
# Stop and remove all containers/volumes
docker-compose -f docker-compose.dev.yml down --volumes --remove-orphans
docker-compose -f docker-compose.prod.yml down --volumes --remove-orphans

# Clean system
docker system prune -f
```

### Backups (Production)
```bash
# Database backup
docker exec agent-builder-postgres-prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Volume backup
docker run --rm -v agent-builder-postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
```

### Updates
```bash
# Rebuild with latest changes
docker-compose -f docker-compose.dev.yml up -d --build

# Production deployment
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 5000, 5173, 5432, 6379, etc. are available
2. **Permission Issues**: The containers run as non-root users for security
3. **Missing .env**: Create .env.prod for production deployments
4. **TFrameX Version**: Update pyproject.toml if you need a different TFrameX version

### Logs
```bash
# View specific service logs
docker-compose -f docker-compose.dev.yml logs backend
docker-compose -f docker-compose.dev.yml logs frontend

# Follow logs in real-time
docker-compose -f docker-compose.dev.yml logs -f
```

### Health Checks
```bash
# Check service health
docker-compose -f docker-compose.dev.yml ps

# Manual health check
curl http://localhost:5000/health
curl http://localhost:5173/
```

## Next Steps

1. Customize environment variables for your setup
2. Set up CI/CD pipelines using the Docker configurations
3. Set up monitoring solutions if needed (Prometheus, Grafana, etc.)
4. Set up automated backups
5. Consider Kubernetes deployment for large-scale production

The Docker setup is production-ready and follows industry best practices for containerized applications.