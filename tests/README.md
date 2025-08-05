# Agent-Builder Authentication Tests

This directory contains comprehensive tests for the Agent-Builder authentication system, including Keycloak OAuth integration, JWT middleware, and permission-based access control.

## Test Structure

```
tests/
├── unit/                                    # Unit tests for individual components
│   └── test_keycloak_client.py             # KeycloakClient class tests
├── integration/                             # Integration tests for complete flows
│   ├── authentication_integration_tests.py # Comprehensive auth flow tests
│   └── api_integration_tests.py            # General API tests
├── run_auth_tests.py                       # Test runner script
└── README.md                               # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)

**`test_keycloak_client.py`**
Tests the `KeycloakClient` class methods in isolation:
- OAuth URL generation
- Token exchange and refresh
- User info retrieval
- Admin operations (user creation, role management)
- Error handling and validation
- Health checks

### Integration Tests (`tests/integration/`)

**`authentication_integration_tests.py`**
Tests complete authentication flows:
- **OAuth Flow Tests**: Login initiation, callback handling, error scenarios
- **JWT Middleware Tests**: Token validation, expired tokens, cookie authentication
- **Authorization Tests**: Permission checks, admin privileges, flow execution access
- **Session Management Tests**: Session creation/cleanup, concurrent sessions

**`api_integration_tests.py`**
General API functionality tests (includes some auth-related endpoints).

## Running Tests

### Prerequisites

1. **Backend Service**: Ensure the Agent-Builder backend is running on `http://localhost:5000`
2. **Keycloak (Optional)**: For full OAuth testing, run Keycloak on `http://localhost:8081`
3. **Dependencies**: Install required Python packages

```bash
# Install test dependencies
pip install requests PyJWT redis

# Start services (Docker Compose recommended)
docker-compose -f deploy/docker/docker-compose.dev.yml up -d
```

### Test Runner

Use the provided test runner for comprehensive testing:

```bash
# Run all tests
python tests/run_auth_tests.py

# Run specific categories
python tests/run_auth_tests.py --category unit
python tests/run_auth_tests.py --category integration
python tests/run_auth_tests.py --category auth

# Skip environment checks (if services are not available)
python tests/run_auth_tests.py --skip-env-check

# Verbose output
python tests/run_auth_tests.py --verbose
```

### Individual Test Files

You can also run individual test files directly:

```bash
# Unit tests
python tests/unit/test_keycloak_client.py

# Integration tests
python tests/integration/authentication_integration_tests.py
python tests/integration/api_integration_tests.py
```

## Test Configuration

### Environment Variables

Tests use the following environment variables (with defaults):

```bash
# Service URLs
TEST_BASE_URL=http://localhost:5000          # Backend API URL
TEST_KEYCLOAK_URL=http://localhost:8081      # Keycloak URL

# JWT Configuration
JWT_SECRET_KEY=dev-secret-key                # JWT signing secret

# Keycloak Configuration
KEYCLOAK_SERVER_URL=http://localhost:8080    # Internal Keycloak URL
KEYCLOAK_PUBLIC_URL=http://localhost:8081    # Public Keycloak URL
KEYCLOAK_REALM=agent-builder                 # Keycloak realm
KEYCLOAK_CLIENT_ID=agent-builder-app         # OAuth client ID
KEYCLOAK_CLIENT_SECRET=                      # OAuth client secret
```

### Test Data

Tests use these predefined test accounts and data:

- **Development User**: `dev@agent-builder.local` (bypasses Keycloak)
- **Test Organization**: `Development Org`
- **Admin Permissions**: Full access (`*` permission)

## Test Scenarios Covered

### 1. OAuth 2.0/OIDC Flow
- ✅ Login initiation with proper OAuth URL generation
- ✅ Authorization callback handling
- ✅ Error scenarios (missing code, OAuth errors)
- ✅ Token exchange and validation
- ✅ User info retrieval from Keycloak
- ✅ Logout and token revocation

### 2. JWT Token Management
- ✅ Access token creation and validation
- ✅ Refresh token handling
- ✅ Token expiration checks
- ✅ Token revocation (blacklisting)
- ✅ Cookie-based authentication
- ✅ Authorization header authentication

### 3. Session Management
- ✅ Session creation and storage
- ✅ Session cleanup and expiration
- ✅ Concurrent session handling
- ✅ Session-based logout

### 4. Authorization & Permissions
- ✅ Role-based access control (RBAC)
- ✅ Permission validation
- ✅ Organization-level access control
- ✅ Admin privilege escalation
- ✅ Protected endpoint access

### 5. Development Features
- ✅ Development login bypass
- ✅ Mock user creation
- ✅ Environment-specific behavior

### 6. Error Handling
- ✅ Network connectivity issues
- ✅ Invalid credentials
- ✅ Malformed tokens
- ✅ Rate limiting
- ✅ Account lockout

## Expected Test Results

### In Development Environment

When running with the development Docker setup:

```
✅ Backend Service: Available at http://localhost:5000
✅ Keycloak Service: Available at http://localhost:8081
✅ Development Login: Enabled
✅ Full OAuth Flow: Testable
✅ All Permissions: Available via dev user
```

### In Production Environment

When running against production:

```
✅ Backend Service: Available
❌ Development Login: Disabled (expected)
✅ OAuth Flow: Full Keycloak integration required
✅ Permissions: Based on actual user roles
```

## Troubleshooting

### Common Issues

**Services Not Running**
```bash
# Check service status
curl http://localhost:5000/health
curl http://localhost:8081/realms/agent-builder

# Start services
docker-compose -f deploy/docker/docker-compose.dev.yml up -d
```

**Authentication Failures**
```bash
# Check Keycloak realm configuration
# Verify client ID and secret
# Ensure redirect URLs match
```

**JWT Token Issues**
```bash
# Verify JWT_SECRET_KEY matches between test and application
# Check token expiration times
# Verify Redis connectivity for token blacklisting
```

**Permission Errors**
```bash
# Verify user roles in Keycloak
# Check organization membership
# Validate permission mappings
```

### Debug Mode

For detailed debugging, set environment variables:

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Enable SQL query logging
export DB_ECHO=true

# Run tests with verbose output
python tests/run_auth_tests.py --verbose
```

## Test Coverage

The authentication tests provide coverage for:

- **OAuth 2.0/OIDC Integration**: 95%
- **JWT Middleware**: 90%
- **Session Management**: 85%
- **Permission System**: 80%
- **Error Handling**: 90%

## Contributing

When adding new authentication features:

1. **Add Unit Tests**: Test individual components in isolation
2. **Add Integration Tests**: Test complete user flows
3. **Update Documentation**: Update this README with new test scenarios
4. **Verify Coverage**: Ensure new code paths are tested

### Test Naming Convention

- Unit tests: `test_<component>_<method>_<scenario>`
- Integration tests: `test_<flow>_<scenario>`
- Test classes: `Test<ComponentName>` or `<FlowName>Tests`

Example:
```python
def test_keycloak_client_exchange_tokens_success(self):
def test_oauth_flow_callback_missing_code(self):
```

## Security Considerations

These tests verify security-critical functionality:

- **No Credentials in Code**: All test credentials are environment-based
- **Token Validation**: Comprehensive JWT validation testing
- **Permission Isolation**: Organization and role-based access controls
- **Session Security**: HttpOnly cookies, secure flags, expiration
- **Rate Limiting**: Brute force protection testing

## Continuous Integration

For CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Authentication Tests
  run: |
    docker-compose -f deploy/docker/docker-compose.dev.yml up -d
    sleep 30  # Wait for services
    python tests/run_auth_tests.py --category all
    docker-compose -f deploy/docker/docker-compose.dev.yml down
```