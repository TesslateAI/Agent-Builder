# Agent-Builder Production Deployment Guide

This guide covers deploying Agent-Builder to production environments.

## Prerequisites

- Docker and Docker Compose installed
- Domain names configured for:
  - Main application (e.g., `app.example.com`)
  - API backend (e.g., `api.example.com`)
  - Authentication server (e.g., `auth.example.com`)
- SSL certificates (or use Let's Encrypt)
- Minimum server requirements:
  - 4 CPU cores
  - 8GB RAM
  - 50GB storage

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/agent-builder.git
   cd agent-builder
   ```

2. **Configure environment**
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with your production values
   ```

3. **Generate security keys**
   ```bash
   # Generate JWT secret
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Generate Keycloak client secret
   openssl rand -base64 32
   ```

4. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Initialize database**
   ```bash
   docker exec agent-builder-backend python manage_db.py init
   docker exec agent-builder-backend python manage_db.py upgrade
   ```

## Configuration Details

### Environment Variables

Key variables that MUST be configured:

- `JWT_SECRET_KEY` - Secret key for JWT token signing
- `POSTGRES_PASSWORD` - Database password
- `REDIS_PASSWORD` - Redis cache password
- `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin password
- `OPENAI_API_KEY` (or other LLM provider key)

### Database Setup

The application uses PostgreSQL with automatic migrations via Alembic.

```bash
# Create initial migration
docker exec agent-builder-backend python manage_db.py create "Initial schema"

# Apply migrations
docker exec agent-builder-backend python manage_db.py upgrade

# Check current version
docker exec agent-builder-backend python manage_db.py current
```

### Keycloak Configuration

1. Access Keycloak admin console at `https://auth.example.com`
2. Login with admin credentials
3. Import the production realm configuration
4. Configure client redirect URIs for your domains
5. Set up user federation if needed (LDAP, AD, etc.)

### SSL/TLS Setup

#### Option 1: Let's Encrypt (Recommended)

Use the included nginx service with Certbot:

```yaml
# Uncomment nginx service in docker-compose.prod.yml
nginx:
  image: nginx:alpine
  # ... configuration
```

#### Option 2: Custom Certificates

Place certificates in `./nginx/ssl/` and reference in nginx config.

## Monitoring & Maintenance

### Health Checks

Monitor application health:

```bash
# Basic health check
curl https://api.example.com/health

# Detailed health check
curl https://api.example.com/health/detailed

# Kubernetes-style probes
curl https://api.example.com/health/live
curl https://api.example.com/health/ready
```

### Logs

View application logs:

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Backups

#### Database Backup

```bash
# Backup database
docker exec agent-builder-postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i agent-builder-postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql
```

#### Full Backup Script

Create `/etc/cron.daily/agent-builder-backup`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/agent-builder"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker exec agent-builder-postgres pg_dump -U produser agentbuilder | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Redis backup
docker exec agent-builder-redis redis-cli --no-auth-warning -a $REDIS_PASSWORD BGSAVE
docker cp agent-builder-redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Keycloak backup
docker exec agent-builder-keycloak /opt/keycloak/bin/kc.sh export --dir /tmp/export
docker cp agent-builder-keycloak:/tmp/export "$BACKUP_DIR/keycloak_$DATE"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete
```

## Scaling

### Horizontal Scaling

For high availability, deploy multiple backend instances:

```yaml
backend:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
    restart_policy:
      condition: on-failure
```

### Database Scaling

Consider using managed PostgreSQL services:
- AWS RDS
- Google Cloud SQL
- Azure Database

### Caching Strategy

Redis configuration for production:
- Enable persistence (AOF + RDB)
- Set appropriate memory limits
- Configure eviction policies

## Troubleshooting

### Common Issues

1. **Backend won't start**
   - Check database connectivity
   - Verify environment variables
   - Review logs: `docker logs agent-builder-backend`

2. **Authentication failures**
   - Verify Keycloak is running
   - Check redirect URIs match your domain
   - Ensure JWT secret is configured

3. **Frontend can't reach API**
   - Check nginx proxy configuration
   - Verify CORS settings
   - Test API directly: `curl http://backend:5000/health`

### Debug Mode

Enable debug logging:

```bash
# In .env.prod
LOG_LEVEL=DEBUG
FLASK_DEBUG=1  # ONLY for troubleshooting
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated new JWT secret key
- [ ] Configured SSL/TLS certificates
- [ ] Enabled firewall rules
- [ ] Disabled debug mode
- [ ] Set up regular backups
- [ ] Configured log rotation
- [ ] Implemented rate limiting
- [ ] Set up monitoring alerts
- [ ] Reviewed CORS settings

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_flows_created_at ON flows(created_at);
CREATE INDEX idx_flow_executions_started_at ON flow_executions(started_at);

-- Analyze tables
ANALYZE flows;
ANALYZE flow_executions;
```

### Redis Optimization

```redis
# Set memory limit
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru

# Enable compression
CONFIG SET compression yes
```

### Application Tuning

In production configuration:
- Increase worker processes
- Enable response caching
- Optimize database connection pooling
- Configure CDN for static assets

## Support

For production support:
- Documentation: https://docs.agent-builder.com
- Issues: https://github.com/your-org/agent-builder/issues
- Enterprise support: support@agent-builder.com