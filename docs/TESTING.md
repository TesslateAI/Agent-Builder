# Agent-Builder Testing Guide

This guide provides instructions for testing the Agent-Builder application in development and production environments.

## Development Testing

### Prerequisites

- Docker and Docker Compose installed
- Git for version control
- curl or similar HTTP client for API testing

### Quick Start Testing

1. **Start the development environment:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Check container health:**
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

3. **Verify all services are healthy:**
   - Backend: http://localhost:5000/health
   - Frontend: http://localhost:5173
   - Keycloak: http://localhost:8081
   - Redis: `docker exec agent-builder-redis-dev redis-cli ping`
   - PostgreSQL: `docker exec agent-builder-postgres-dev psql -U devuser -d agentbuilder_dev -c "SELECT 1"`

### API Testing

#### Health Checks
```bash
# Basic health check
curl http://localhost:5000/health

# Readiness check (includes database, redis, tframex status)
curl http://localhost:5000/health/ready

# Detailed health check
curl http://localhost:5000/health/detailed

# Liveness probe
curl http://localhost:5000/health/live
```

#### Component Discovery
```bash
# Get all TFrameX components
curl http://localhost:5000/api/tframex/components

# Get specific component types
curl http://localhost:5000/api/tframex/components?type=agents
curl http://localhost:5000/api/tframex/components?type=tools
curl http://localhost:5000/api/tframex/components?type=patterns
```

#### Flow Execution
```bash
# Execute a simple flow
curl -X POST http://localhost:5000/api/tframex/flow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {
        "id": "1",
        "type": "ResearchAgent",
        "data": {
          "label": "Research Assistant",
          "component_category": "agent"
        }
      }
    ],
    "edges": [],
    "params": {
      "message": "What is TFrameX?"
    }
  }'
```

#### Model Management
```bash
# List configured models
curl http://localhost:5000/api/tframex/models

# Test model connectivity
curl -X POST http://localhost:5000/api/tframex/models/test \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model_name": "gpt-3.5-turbo",
    "api_key": "your-api-key"
  }'
```

### Database Testing

#### Initialize Database
```bash
# Initialize with default data
docker exec agent-builder-backend-dev python builder/backend/manage_db.py init

# Run migrations
docker exec agent-builder-backend-dev python builder/backend/manage_db.py upgrade

# Check current migration version
docker exec agent-builder-backend-dev python builder/backend/manage_db.py current
```

#### Test Database Connections
```bash
# Connect to PostgreSQL
docker exec -it agent-builder-postgres-dev psql -U devuser -d agentbuilder_dev

# Basic queries
SELECT * FROM users LIMIT 5;
SELECT * FROM organizations LIMIT 5;
SELECT * FROM projects LIMIT 5;
\dt  # List all tables
\q   # Exit
```

### Frontend Testing

1. **Access the UI:**
   - Open http://localhost:5173 in your browser
   - You should see the TFrameX Studio interface

2. **Test basic functionality:**
   - Drag and drop components from the sidebar
   - Connect components with edges
   - Configure component properties in the right panel
   - Test the "Run Flow" button

3. **Test authentication (if enabled):**
   - Click login button
   - Use test credentials:
     - admin/admin (full access)
     - developer/dev (developer access)
     - user/user (read-only access)

### Integration Testing

#### Test Flow Builder Integration
```bash
# Test the chatbot flow builder
curl -X POST http://localhost:5000/api/tframex/chatbot_flow_builder \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a flow with two agents that discuss a topic"
  }'
```

#### Test MCP Server Integration
```bash
# Check MCP status
curl http://localhost:5000/api/tframex/mcp/status

# Connect to an MCP server (if configured)
curl -X POST http://localhost:5000/api/tframex/mcp/servers/connect \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "example-server"
  }'
```

### Performance Testing

#### Load Testing with Apache Bench
```bash
# Test health endpoint performance
ab -n 1000 -c 10 http://localhost:5000/health/

# Test component listing performance
ab -n 100 -c 5 http://localhost:5000/api/tframex/components
```

#### Memory and Resource Monitoring
```bash
# Monitor container resources
docker stats

# Check specific container logs
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### Debugging

#### Backend Debugging
```bash
# Access backend container
docker exec -it agent-builder-backend-dev bash

# Check Python dependencies
pip list

# Run Python shell for testing
python
>>> from builder.backend.models import User, Organization
>>> from builder.backend.database import get_session
>>> # Test database queries
```

#### Frontend Debugging
1. Open browser developer tools (F12)
2. Check Console for errors
3. Monitor Network tab for API calls
4. Use React Developer Tools extension

### Test Scripts

> **Note**: This is an example test script that you can create for testing the API. Save it as `test_api.py` in your project root.

Create a test script `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoints"""
    endpoints = ["/health", "/health/ready", "/health/live"]
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"{endpoint}: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))

def test_components():
    """Test component discovery"""
    response = requests.get(f"{BASE_URL}/api/tframex/components")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['agents'])} agents")
        print(f"Found {len(data['tools'])} tools")
        print(f"Found {len(data['patterns'])} patterns")

def test_flow_execution():
    """Test simple flow execution"""
    flow = {
        "nodes": [{
            "id": "1",
            "type": "ResearchAgent",
            "data": {"label": "Test Agent", "component_category": "agent"}
        }],
        "edges": [],
        "params": {"message": "Hello, TFrameX!"}
    }
    
    response = requests.post(
        f"{BASE_URL}/api/tframex/flow/execute",
        json=flow,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Flow execution: {response.status_code}")
    if response.status_code == 200:
        print(response.json())

if __name__ == "__main__":
    print("Testing Agent-Builder API...")
    test_health()
    test_components()
    test_flow_execution()
```

Run the test script (after creating it):
```bash
# First, copy the test script to the container (if created locally)
docker cp test_api.py agent-builder-backend-dev:/app/test_api.py

# Then run it
docker exec agent-builder-backend-dev python /app/test_api.py
```

## Production Testing

### Pre-deployment Checklist

- [ ] All environment variables configured in `.env.prod`
- [ ] SSL certificates ready (or Let's Encrypt configured)
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Error tracking (Sentry) configured

### Smoke Tests

After deployment, run these basic tests:

1. **Health checks:**
   ```bash
   curl https://api.example.com/health
   curl https://api.example.com/health/ready
   ```

2. **Authentication:**
   ```bash
   # Test login flow
   curl -X POST https://api.example.com/api/auth/login
   ```

3. **Core functionality:**
   - Access the UI at https://example.com
   - Create a simple flow
   - Execute the flow
   - Check results

### Monitoring

Set up monitoring for:
- Response times
- Error rates
- Database connection pool
- Redis memory usage
- Container resource usage

## Troubleshooting

### Common Issues

1. **Container won't start:**
   - Check logs: `docker-compose logs <service>`
   - Verify environment variables
   - Check port conflicts

2. **Database connection errors:**
   - Verify PostgreSQL is running
   - Check connection string
   - Test with psql directly

3. **Frontend can't reach backend:**
   - Check CORS configuration
   - Verify API_URL environment variable
   - Test backend endpoints directly

4. **Authentication failures:**
   - Check Keycloak is running
   - Verify redirect URIs
   - Check JWT configuration

### Debug Commands

```bash
# Check container health
docker inspect agent-builder-backend-dev | jq '.[0].State.Health'

# View environment variables
docker exec agent-builder-backend-dev env | sort

# Check network connectivity
docker exec agent-builder-backend-dev ping postgres

# Database connection test
docker exec agent-builder-backend-dev python -c "from builder.backend.database import engine; print(engine.url)"
```

## Continuous Testing

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build containers
      run: docker-compose -f docker-compose.test.yml build
    
    - name: Run tests
      run: docker-compose -f docker-compose.test.yml run test
    
    - name: Clean up
      run: docker-compose -f docker-compose.test.yml down -v
```

### Local Test Runner

Create `run_tests.sh`:

```bash
#!/bin/bash
set -e

echo "Starting test environment..."
docker-compose -f docker-compose.dev.yml up -d

echo "Waiting for services to be ready..."
sleep 10

echo "Running API tests..."
docker exec agent-builder-backend-dev pytest tests/

echo "Running integration tests..."
# Run the test script if it exists
if [ -f "test_api.py" ]; then
    python test_api.py
else
    echo "test_api.py not found - create it using the example above"
fi

echo "Test completed!"
```

Make it executable:
```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Test Coverage

To check test coverage:

```bash
# Install coverage tool
docker exec agent-builder-backend-dev pip install coverage

# Run tests with coverage
docker exec agent-builder-backend-dev coverage run -m pytest

# Generate coverage report
docker exec agent-builder-backend-dev coverage report
docker exec agent-builder-backend-dev coverage html
```

## Load Testing

For production-grade load testing:

1. **Use Locust:**
   ```python
   from locust import HttpUser, task, between
   
   class AgentBuilderUser(HttpUser):
       wait_time = between(1, 3)
       
       @task
       def health_check(self):
           self.client.get("/health")
       
       @task(3)
       def get_components(self):
           self.client.get("/api/tframex/components")
   ```

2. **Run load test:**
   ```bash
   locust -f locustfile.py --host=http://localhost:5000
   ```

## Security Testing

1. **Check security headers:**
   ```bash
   curl -I http://localhost:5000
   ```

2. **Test authentication:**
   - Attempt unauthorized access
   - Test token expiration
   - Verify CORS policies

3. **SQL injection tests:**
   - Use parameterized queries
   - Test with OWASP ZAP or similar tools