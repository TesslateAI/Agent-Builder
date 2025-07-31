# Agent-Builder Authentication System

This document describes the enterprise authentication and authorization system implemented in Agent-Builder v1.1.0.

## Overview

Agent-Builder now includes a comprehensive authentication system built on:

- **Keycloak**: OAuth 2.0/OIDC identity provider
- **JWT Tokens**: Stateless authentication with Redis session management  
- **RBAC**: Role-based access control with hierarchical permissions
- **Multi-tenancy**: Organization-based isolation
- **Audit Logging**: Complete audit trail for compliance

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   Browser   │───▶│    Traefik   │───▶│  Agent-     │───▶│  PostgreSQL │
│             │    │   (Reverse   │    │  Builder    │    │  (Database) │
│             │    │    Proxy)    │    │   Backend   │    └─────────────┘
└─────────────┘    └──────────────┘    └─────────────┘    
                            │                 │
                            ▼                 ▼
                   ┌──────────────┐    ┌─────────────┐
                   │   Keycloak   │    │    Redis    │
                   │  (Auth IDP)  │    │ (Sessions)  │
                   └──────────────┘    └─────────────┘
```

## Authentication Flow

1. **User Access**: User attempts to access protected resource
2. **Redirect**: Backend redirects to Keycloak login
3. **Authentication**: User logs in via Keycloak OAuth flow  
4. **Token Exchange**: Keycloak returns authorization code
5. **JWT Creation**: Backend creates JWT tokens and Redis session
6. **Protected Access**: User can access protected resources with JWT

## Components

### 1. JWT Middleware (`builder/backend/middleware/auth.py`)

Handles JWT token validation and user context:

```python
@require_auth
def protected_route():
    user_id = get_current_user_id()
    organization_id = get_current_organization_id()
    # Route logic
```

**Key Features:**
- JWT token validation
- Redis session management
- Token blacklisting for logout
- Request context injection

### 2. Keycloak Integration (`builder/backend/auth/keycloak_client.py`)

OAuth 2.0/OIDC client for Keycloak:

```python
class KeycloakClient:
    def get_authorization_url(self, state, scopes)
    def exchange_code_for_tokens(self, code) 
    def get_user_info(self, access_token)
    def logout_user(self, refresh_token)
```

**Configuration:**
- Realm: `agent-builder`
- Client ID: `agent-builder-app` 
- Flow: Authorization Code with PKCE
- Scopes: `openid profile email roles`

### 3. RBAC System (`builder/backend/auth/rbac.py`)

Hierarchical permission system:

```python
@require_permission('flows.execute')
def execute_flow():
    # Only users with flows.execute permission can access
```

**Permission Hierarchy:**
- `*`: All permissions (admin)
- `admin`: Full administrative access
- `flows.*`: All flow operations  
- `flows.execute`: Execute flows only
- `projects.read`: Read project access

**Default Roles:**
- **Organization Admin**: Full access (`*`)
- **Developer**: Create/execute flows, read projects
- **User**: Execute flows, read projects

### 4. Database Schema (`builder/backend/database.py`)

Enterprise tables for multi-tenancy:

```sql
-- Organizations (multi-tenant isolation)
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    settings TEXT -- JSON config
);

-- Users with organization membership  
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    keycloak_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    organization_id TEXT NOT NULL
);

-- Hierarchical roles system
CREATE TABLE roles (
    id TEXT PRIMARY KEY, 
    name TEXT NOT NULL,
    permissions TEXT NOT NULL, -- JSON array
    organization_id TEXT NOT NULL
);

-- Project-specific role assignments
CREATE TABLE user_project_roles (
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL, 
    role_id TEXT NOT NULL
);

-- Complete audit logging
CREATE TABLE audit_logs (
    user_id TEXT,
    organization_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT, -- JSON
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Authentication Routes (`builder/backend/routes/auth.py`)

RESTful auth API:

- `GET /api/auth/login`: Initiate OAuth flow
- `GET /api/auth/callback`: Handle OAuth callback  
- `POST /api/auth/logout`: Logout and revoke tokens
- `GET /api/auth/user`: Get current user info
- `GET /api/auth/health`: Check auth system health

### 6. Frontend Auth Context (`builder/frontend/src/contexts/AuthContext.jsx`)

React authentication state management:

```jsx
const { user, login, logout, hasPermission } = useAuth();

// Check permissions
if (hasPermission('flows.create')) {
    // Show create flow button
}

// Protected routes
<ProtectedRoute permission="flows.read">
    <FlowEditor />
</ProtectedRoute>
```

## Development Setup

### 1. Start Development Environment

```bash
# Start all services including Keycloak
docker-compose -f docker-compose.dev.yml up -d

# Check services
docker-compose -f docker-compose.dev.yml ps
```

### 2. Access Development Services

- **Application**: http://localhost:5173
- **Backend API**: http://localhost:5000  
- **Keycloak Admin**: http://localhost:8081 (admin/admin)
- **PostgreSQL**: localhost:5432 (devuser/devpass)
- **Redis**: localhost:6379

### 3. Test Users (Development)

Pre-configured in dev realm:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| admin | admin | Administrators | * (all) |
| developer | dev | Developers | flows.*, projects.read |  
| user | user | Users | flows.read, flows.execute |

### 4. Test Authentication Flow

1. Visit http://localhost:5173
2. Click login → redirects to Keycloak
3. Login with test credentials
4. Redirected back with authentication
5. Access protected features based on role

## Production Deployment  

### 1. Environment Configuration

```bash
# Copy and configure production environment
cp .env.prod.example .env.prod

# Update required values:
# - DOMAIN=your-domain.com
# - All passwords and secrets
# - JWT_SECRET_KEY (generate with secrets.token_hex(32))
# - KEYCLOAK_CLIENT_SECRET
# - Database passwords
```

### 2. SSL/TLS Setup

Traefik automatically provisions Let's Encrypt certificates:

```yaml
# Keycloak accessible at https://auth.your-domain.com  
# Application at https://your-domain.com
```

### 3. Keycloak Production Configuration

Update `keycloak/production-realm.json`:

1. Change client secret from placeholder
2. Update redirect URIs for production domain
3. Enable email verification
4. Configure strong password policies
5. Disable user registration (admin-only user creation)

### 4. Deploy Production Stack

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Check deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs

# Access Keycloak admin
# https://auth.your-domain.com
```

### 5. Create Production Users

1. Access Keycloak admin console
2. Navigate to Users → Add User
3. Set email, first/last name
4. Assign to appropriate groups (Administrators, Developers, Users)
5. Set initial password (force password change on first login)

### 6. Security Hardening

**Network Security:**
- Use internal Docker networks
- Expose only necessary ports via Traefik
- Configure firewalls/security groups

**Secrets Management:**  
- Store secrets in secure password manager
- Use Docker secrets or external secret managers
- Rotate JWT secrets regularly

**Monitoring:**
- Enable audit logging (`AUDIT_ENABLED=true`)
- Monitor authentication failures
- Set up alerting for suspicious activity
- Aggregate logs to SIEM system

## API Integration

### Protected API Usage

All API endpoints require authentication:

```bash
# Login to get JWT token (stored in httpOnly cookie)
curl -X GET http://localhost:5000/api/auth/login

# Access protected endpoints (cookies sent automatically)
curl -X GET http://localhost:5000/api/tframex/projects \
  --cookie-jar cookies.txt --cookie cookies.txt

# Or use Authorization header
curl -X GET http://localhost:5000/api/tframex/projects \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Permission-Based Access

Routes are protected by specific permissions:

| Endpoint | Permission Required | Description |
|----------|-------------------|-------------|
| `GET /api/tframex/components` | None | Public component list |
| `GET /api/tframex/projects` | `projects.read` | List projects |
| `POST /api/tframex/projects` | `projects.create` | Create project |
| `POST /api/tframex/register_code` | `flows.create` | Register new component |
| `POST /api/tframex/flow/execute` | `flows.execute` | Execute workflow |

### Error Responses

```json
// No authentication
{
  "error": "Authentication required", 
  "message": "No authentication token provided"
}

// Insufficient permissions
{
  "error": "Insufficient permissions",
  "message": "Permission 'flows.create' required" 
}

// Invalid/expired token
{
  "error": "Invalid token",
  "message": "Token has expired"
}
```

## Troubleshooting

### Common Issues

**1. Keycloak Connection Failed**
```bash
# Check Keycloak is running
docker-compose -f docker-compose.dev.yml logs keycloak

# Verify database connectivity
docker-compose -f docker-compose.dev.yml exec postgres psql -U devuser -l
```

**2. JWT Token Issues**
```bash
# Check Redis connectivity
docker-compose -f docker-compose.dev.yml exec redis redis-cli ping

# Verify JWT secret is configured
echo $JWT_SECRET_KEY
```

**3. Permission Denied**
- Check user is assigned to correct Keycloak groups
- Verify group has required permissions in realm configuration
- Check audit logs for permission failures

**4. Database Migration Issues**
```bash
# Reset development database
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### Debug Mode

Enable detailed authentication logging:

```bash
# Set debug logging
LOG_LEVEL=DEBUG

# Check authentication middleware logs
docker-compose -f docker-compose.dev.yml logs backend | grep auth
```

## Security Considerations

### Production Checklist

- [ ] All default passwords changed
- [ ] Strong JWT secret key (32+ chars)
- [ ] HTTPS enabled everywhere  
- [ ] Email verification enabled
- [ ] Strong password policies
- [ ] User registration disabled
- [ ] Audit logging enabled
- [ ] Session timeouts configured
- [ ] Network segmentation in place
- [ ] Container vulnerability scanning
- [ ] Backup strategies implemented
- [ ] Monitoring and alerting configured

### Regular Maintenance

- **Weekly**: Review audit logs for suspicious activity
- **Monthly**: Rotate JWT secrets and client credentials
- **Quarterly**: Review user permissions and access
- **Annually**: Security audit and penetration testing

## Migration from Legacy

For existing installations without authentication:

1. **Backup Data**: Export existing projects and flows
2. **Deploy New Version**: Use docker-compose.prod.yml
3. **Create Admin User**: Via Keycloak admin console  
4. **Import Data**: Assign ownership to admin user
5. **Create User Accounts**: For existing users
6. **Test Access**: Verify all functionality works

Legacy API access will be blocked - all clients must implement OAuth flow.

## Support

For authentication-related issues:

1. Check logs: `docker-compose logs backend keycloak`
2. Verify configuration in `.env` file
3. Test with curl commands above
4. Review Keycloak admin console for user/role issues
5. Check audit logs in database for detailed error tracking

The authentication system provides enterprise-grade security while maintaining ease of use for developers and end users.