# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent-Builder is a visual flow builder for TFrameX v1.1.0 - a React-based drag-and-drop interface for creating multi-agent LLM workflows. Users design flows visually that execute via TFrameX's orchestration engine.

**Architecture:**
- **Frontend**: React + ReactFlow (visual canvas) + Zustand (state) + shadcn/ui + Vite
- **Backend**: Flask API that translates visual flows to executable TFrameX flows  
- **Core Integration**: TFrameX v1.1.0 for LLM orchestration with MCP (Model Context Protocol) support

## Common Commands

### Development Setup
```bash
# PRIMARY: Docker Compose Development Environment (RECOMMENDED)
docker-compose -f docker-compose.dev.yml up -d  # Start all services
docker-compose -f docker-compose.dev.yml logs -f  # Check logs for debugging
docker-compose -f docker-compose.dev.yml down     # Stop all services

# Alternative: Quick start with local TFrameX
./start-dev.sh  # Assumes ../TFrameX directory exists

# Alternative: Python start script
python start-dev.py  # or python3 on some systems

# Alternative: Manual setup with Make
make install-dev  # Install all dependencies including dev tools
make run-dev      # Run both backend and frontend in dev mode
```

### Build & Production
```bash
# Production build and run
make install      # Install dependencies and build frontend
make run          # Run in production mode (backend serves built frontend)

# Frontend only commands
cd builder/frontend
npm install       # Install dependencies
npm run build     # Build for production
npm run dev       # Development server with hot reload
npm run lint      # Run ESLint
```

### Code Quality
```bash
# Python linting and formatting
make lint         # Run ruff on Python code
make format       # Format with black and fix with ruff

# Run tests
make test         # Runs builder/backend/test_v1.1.0.py

# Frontend linting
cd builder/frontend && npm run lint
```

### Docker
```bash
# Development Environment (PRIMARY)
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs backend  # Check backend logs
docker-compose -f docker-compose.dev.yml logs frontend # Check frontend logs

# Production Build
make docker-build  # Build Docker image
make docker-run    # Run container (requires OPENAI_API_KEY env var)

# Production Deployment with Authentication
cp .env.prod.example .env.prod  # Copy and configure production environment
docker-compose -f docker-compose.prod.yml up -d  # Deploy production stack
docker-compose -f docker-compose.prod.yml logs   # Check deployment logs
```

## Code Architecture

### Backend Structure (Flask + TFrameX)

**Key Files:**
- `builder/backend/tframex_config.py`: Global TFrameX app instance initialization, MCP configuration, and two pre-registered agents (ConversationalAssistant, FlowBuilderAgent)
- `builder/backend/app.py`: Flask server with API endpoints for component discovery, flow execution, model management, and dynamic code registration
- `builder/backend/flow_translator.py`: Core logic that converts ReactFlow visual graphs to executable TFrameX Flow objects with multi-model support
- `builder/backend/component_manager.py`: Introspects TFrameX app to discover available agents/tools/patterns

**TFrameX Integration Pattern:**
```python
# All components must register with the global instance
from tframex_config import get_tframex_app_instance
tframex_app = get_tframex_app_instance()

@tframex_app.agent(name="my_agent", description="...")
async def my_agent(message: str) -> str:
    return f"Processed: {message}"
```

### Frontend Structure (React + ReactFlow)

**Key Components:**
- `builder/frontend/src/store.js`: Zustand store managing flow state, component registry, model configurations, and localStorage persistence
- `builder/frontend/src/App.jsx`: Main layout with ReactFlow canvas and surrounding panels
- `builder/frontend/src/nodes/tframex/`: Node components for each TFrameX type (agents, patterns, tools)
- `builder/frontend/src/components/ModelConfigurationPanel.jsx`: Multi-provider LLM model management interface
- `builder/frontend/src/components/PropertiesPanel.jsx`: Node properties editor with model selection

**Handle Connection Types:**
- **Blue handles**: Standard message/data flow between components
- **Purple handles**: Tool-to-agent connections (enables tools for agents)
- **Amber handles**: Pattern parameter assignments (e.g., router agent)
- **Green handles**: List-based pattern parameters (e.g., discussion participants)

## Development Guidelines

### Code Quality & Preferences

- **Always prefer simple solutions** - Choose the most straightforward approach that solves the problem effectively
- **Avoid code duplication** - Before implementing new functionality, check existing codebase for similar code and reuse/refactor where possible
- **Keep files manageable** - Refactor files that exceed 200-300 lines of code to maintain readability and maintainability
- **Multi-environment awareness** - Write code that properly handles dev, test, and prod environments
- **No fake data in non-test environments** - Mocking data is only for tests; never add stubbing or fake data patterns for dev or prod
- **Environment file protection** - Never overwrite `.env` files without explicit confirmation

### Change Management

- **Surgical changes only** - Make only the requested changes or those you're confident are well-understood and directly related
- **Exhaust existing patterns first** - When fixing bugs, try all options within existing implementation before introducing new patterns/technologies
- **Clean up deprecated code** - If new patterns are introduced, remove old implementations to prevent duplicate logic
- **No one-time scripts** - Avoid writing scripts in files, especially for one-time use cases
- **Maintain clean structure** - Keep the codebase well-organized and follow established patterns

### Environment Setup
Before any Python development:
```bash
source .venv/Scripts/activate  # Windows
# or
source .venv/bin/activate      # Unix/Mac
```

### Environment Variables
Required for LLM access (in `.env` or environment):
- `OPENAI_API_KEY` / `OPENAI_API_BASE` - For OpenAI/compatible APIs
- `LLAMA_API_KEY` / `LLAMA_BASE_URL` / `LLAMA_MODEL` - For Ollama/local models
- `MCP_CONFIG_FILE` - Path to MCP servers config (default: `servers_config.json`)

**Authentication Variables (Production):**
- `JWT_SECRET_KEY` - JWT token signing secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin password
- `KEYCLOAK_CLIENT_SECRET` - OAuth client secret
- `REDIS_PASSWORD` - Redis session store password
- `POSTGRES_PASSWORD` - Database password

**Docker Development Environment:**
- Uses `docker-compose.dev.yml` with hot reload for both frontend and backend
- Includes Redis, PostgreSQL, Ollama, Keycloak, and development tools (PgAdmin, RedisInsight)
- Backend runs on port 5000, Frontend on port 5173
- Keycloak authentication server on port 8081 (admin console at http://localhost:8081)
- Ollama available at port 11434 for local LLM testing

### Override System
UI configurations create **runtime overrides** without modifying base TFrameX definitions:
- System prompts, tool selections, template variables are applied per-execution
- Blue dot indicator shows nodes with active overrides
- Base agent/tool definitions remain unchanged unless re-registered via "Add Code" panel

### Dynamic Code Registration
Users can add new TFrameX components via the "Add Code" panel:
- Code must use `@tframex_app.agent(...)` or `@tframex_app.tool(...)` decorators
- Backend executes the code and registers components with the running app
- New components appear immediately in the component palette

### ReactFlow Node Updates
When modifying node data, always use the store's `updateNodeData` method:
```jsx
const updateNodeData = useStore((state) => state.updateNodeData);
// Use callbacks to update data
const handleChange = useCallback((evt) => {
  updateNodeData(id, { [evt.target.name]: evt.target.value });
}, [id, updateNodeData]);
```

## TFrameX v1.1.0 Features

- **MCP Support**: Configure external services via `servers_config.json`
- **Multi-LLM**: OpenAI, Anthropic, Ollama support via environment config and UI model management
- **Enhanced Patterns**: Sequential, Parallel, Router, Discussion with visual configuration
- **Agent-as-Tool**: Connect agents to other agents for delegation
- **strip_think_tags**: Remove thinking tags from agent responses
- **Per-Agent Model Selection**: Each agent can use different LLM models with runtime overrides

## Common Development Tasks

### Adding a New TFrameX Component Type
1. Create node component in `builder/frontend/src/nodes/`
2. Register in `builder/frontend/src/App.jsx` nodeTypes
3. Update `builder/backend/component_manager.py` if new category needed
4. Add to component palette in sidebar

### Modifying Flow Execution
- Edit `builder/backend/flow_translator.py` for graph-to-flow conversion logic
- Handle overrides in `_create_temporary_agent_with_overrides()`
- Update topological sorting if new connection types added

### Testing New Agents/Tools
1. Use "Add Code" panel to register dynamically
2. Or add to `builder/backend/tframex_config.py` for persistent availability
3. Configure model for agent via PropertiesPanel if needed
4. Test execution via "Run Flow" button
5. Check Output panel for results and logs
6. For Docker development, use `docker-compose -f docker-compose.dev.yml logs backend` for debugging

### Adding New LLM Models
1. Click "Models" button in top bar to open ModelConfigurationPanel
2. Select provider (OpenAI, Anthropic, Ollama, Custom)
3. Enter model details and API credentials
4. Test connection before saving
5. Assign models to specific agents via PropertiesPanel
6. Models are stored in `MODEL_CONFIGS` (backend memory - can be moved to database later)

### Docker Development Environment
**Services:**
- **Backend**: Flask API with hot reload (`builder/backend` mounted)
- **Frontend**: React/Vite with HMR (`builder/frontend` mounted)
- **Redis**: Caching and session management (port 6379)
- **PostgreSQL**: Enterprise features and persistence (port 5432)
- **Keycloak**: OAuth2/OIDC authentication server (port 8081)
- **Ollama**: Local LLM server (port 11434)
- **Traefik**: Reverse proxy with dashboard (port 8080)
- **RedisInsight**: Redis GUI (port 8001)
- **PgAdmin**: PostgreSQL GUI (port 8002)

**Development Workflow:**
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check if services are running
docker-compose -f docker-compose.dev.yml ps

# View logs for debugging
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend

# Access applications
# Frontend: http://localhost:5173
# Backend API: http://localhost:5000
# Keycloak Admin: http://localhost:8081 (admin/admin)
# Ollama: http://localhost:11434
# Traefik Dashboard: http://localhost:8080
```

## Authentication System

Agent-Builder includes enterprise-grade authentication and authorization:

### Authentication Architecture
- **Keycloak**: OAuth 2.0/OIDC identity provider with realm `agent-builder`
- **JWT Tokens**: Stateless authentication with Redis session management
- **RBAC**: Role-based access control with hierarchical permissions
- **Multi-tenancy**: Organization-based isolation (enterprise features)

### Key Authentication Files
- `builder/backend/auth/keycloak_client.py`: Keycloak OAuth integration
- `builder/backend/middleware/auth.py`: JWT middleware and session management
- `builder/backend/auth/rbac.py`: Role-based access control system
- `builder/backend/routes/auth.py`: Authentication API endpoints
- `builder/frontend/src/contexts/AuthContext.jsx`: React authentication context
- `builder/frontend/src/components/auth/`: Login, protected routes, user profile

### Development Test Users
Pre-configured in development realm:
- **admin/admin**: Full administrator access (all permissions)
- **developer/dev**: Developer role (flows.*, projects.read)
- **user/user**: User role (flows.read, flows.execute)

### Authentication Flow
1. User accesses protected resource → redirected to Keycloak
2. User authenticates via OAuth flow → authorization code returned
3. Backend exchanges code for JWT tokens → Redis session created
4. Subsequent requests use JWT for authorization

### Production Deployment
- Use `.env.prod.example` as template for production configuration
- Deploy with `docker-compose -f docker-compose.prod.yml up -d`
- Keycloak accessible at `https://auth.your-domain.com`
- Application at `https://your-domain.com`
- See `AUTHENTICATION.md` for complete deployment guide

## Project-Specific Patterns

### Two-Agent AI Assistant Architecture
The project includes two pre-configured agents for the AI Flow Builder:
1. **ConversationalAssistant**: Natural language interface for users
2. **FlowBuilderAgent**: Converts instructions to ReactFlow JSON

Communication flow:
- User chats with ConversationalAssistant
- Assistant ends response with `FLOW_INSTRUCTION: [instruction]`
- FlowBuilderAgent receives instruction and outputs JSON

### State Persistence
- Flow designs saved to localStorage under `tframexStudioProjects`
- Multiple projects supported with project switching
- Auto-save on every node/edge change

### Model Configuration System
- **UI Model Management**: Add/remove/test multiple LLM providers via ModelConfigurationPanel
- **Per-Agent Model Selection**: Configure different models for each agent in PropertiesPanel
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama, and custom OpenAI-compatible APIs
- **Model Testing**: Built-in connectivity testing before saving configurations
- **Visual Indicators**: Blue dots show modified agents, model names displayed in agent nodes
- **Runtime Model Override**: `data.model` field in agent nodes triggers `_create_llm_from_model_name()`

### Error Handling
- Backend validates all flow configurations before execution
- Missing required parameters caught during translation
- Clear error messages returned to UI Output panel
- Model connectivity issues caught during testing and execution