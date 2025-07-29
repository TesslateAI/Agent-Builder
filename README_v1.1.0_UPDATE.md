# Agent-Builder for TFrameX v1.1.0 - Update Documentation

This document details the updates made to Agent-Builder to support TFrameX v1.1.0, which introduces significant enhancements including MCP integration, enterprise features, and improved APIs.

## Major Updates Summary

### 1. **TFrameX Version Update**
- Updated from TFrameX 0.1.3 to 1.1.0
- Complete API modernization and feature integration

### 2. **MCP (Model Context Protocol) Integration**
- Added support for MCP servers configuration
- Enhanced component discovery to show MCP tools
- Agents can now use external MCP tools via `mcp_tools_from_servers`
- MCP meta-tools automatically available when MCP is configured

### 3. **Enhanced LLM Configuration**
- Support for multiple LLM providers (OpenAI, Llama, Ollama)
- Environment variable detection for flexible configuration
- Better error handling and logging

### 4. **Improved Component Discovery**
- Discovers MCP servers and their available tools
- Better categorization of tools (native vs MCP)
- Enhanced parameter schema handling
- Support for v1.1.0 agent features

### 5. **Updated API Usage**
- Migrated from deprecated APIs to v1.1.0 patterns:
  - `rt.call_agent()` → `rt.execute_agent()`
  - `rt.run_flow()` → `rt.execute_flow()`
- Better async context management
- Improved error handling

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-3.5-turbo

# OR Llama/Compatible Configuration
LLAMA_API_KEY=your_key
LLAMA_BASE_URL=https://api.llama.com/compat/v1/
LLAMA_MODEL=Llama-4-Maverick-17B

# OR Local Ollama
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL_NAME=llama3

# MCP Configuration (optional)
MCP_CONFIG_FILE=servers_config.json
```

### MCP Configuration

Create `servers_config.json` in the backend directory:

```json
{
  "mcpServers": {
    "example_stdio": {
      "type": "stdio",
      "command": "python",
      "args": ["example_mcp_server.py"],
      "env": {},
      "init_step_timeout": 30.0,
      "tool_call_timeout": 60.0
    },
    "aws_docs": {
      "type": "stdio",
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {},
      "init_step_timeout": 30.0,
      "tool_call_timeout": 60.0
    }
  }
}
```

## New Features Available in Agent-Builder

### 1. **MCP Tools in Agents**
Agents can now access external MCP tools:
```python
@tframex_app.agent(
    name="DocumentationAgent",
    mcp_tools_from_servers=["aws_docs"],  # Use tools from AWS docs MCP server
    system_prompt="You help with AWS documentation queries"
)
async def doc_agent():
    pass
```

### 2. **Enhanced Agent Configuration**
- `strip_think_tags`: Remove `<think>` tags from output
- `max_tool_iterations`: Control tool call limits
- `mcp_tools_from_servers`: Access external MCP tools

### 3. **Better Tool Discovery**
The component discovery now shows:
- Native TFrameX tools
- MCP meta-tools (for listing/reading MCP resources)
- External MCP tools (from connected servers)

### 4. **Improved Flow Execution**
- Better error handling and logging
- Support for flow template variables
- Enhanced shared data management

## Usage

### Starting the Backend

```bash
cd builder/backend
pip install -r requirements.txt
python app.py
```

### Starting the Frontend

```bash
cd builder/frontend
npm install
npm run dev
```

## API Endpoints

### Component Discovery
```
GET /api/tframex/components
```
Returns agents, tools, patterns, and MCP servers.

### Dynamic Code Registration
```
POST /api/tframex/register_code
```
Register new agents/tools dynamically.

### Flow Execution
```
POST /api/tframex/flow/execute
```
Execute a visual flow with v1.1.0 features.

### Chatbot Flow Builder
```
POST /api/tframex/chatbot_flow_builder
```
AI-assisted flow creation using the meta-agent.

## Example: Using MCP Tools

```python
# Register an agent that uses AWS documentation MCP tools
@tframex_app.agent(
    name="AWSExpert",
    description="Expert on AWS services using documentation",
    mcp_tools_from_servers="ALL",  # Access all MCP tools
    system_prompt="You are an AWS expert. Use the available MCP tools to answer questions."
)
async def aws_expert():
    pass

# The agent can now use:
# - aws_docs__search_documentation
# - aws_docs__get_service_info
# - tframex_list_mcp_servers
# - tframex_list_mcp_resources
# etc.
```

## Migration Notes

When migrating existing Agent-Builder projects:

1. Update `requirements.txt` to use `tframex==1.1.0`
2. Update environment variables for LLM configuration
3. Add MCP configuration if using external services
4. Review agent definitions for new features
5. Test flows with the updated execution APIs

## Troubleshooting

### MCP Not Working
- Check `servers_config.json` exists and is valid
- Verify MCP server commands are available
- Check logs for MCP initialization errors

### Agent Not Found
- Ensure agents are registered with the global app
- Check for typos in agent names
- Verify the agent decorator syntax

### Tool Execution Errors
- Validate tool signatures match v1.1.0 patterns
- Check tool parameter schemas
- Review async/await usage

## Future Enhancements

1. **Enterprise Features Integration**
   - Add authentication/authorization UI
   - Metrics dashboard
   - Multi-backend storage configuration

2. **Advanced MCP Features**
   - MCP roots explorer
   - MCP sampling interface
   - Dynamic MCP server management

3. **CLI Integration**
   - Use `tframex` CLI commands
   - Project scaffolding integration
   - Web server deployment options

## Contributing

Please ensure all contributions:
- Follow TFrameX v1.1.0 patterns
- Include proper error handling
- Add appropriate logging
- Update documentation
- Include tests where applicable