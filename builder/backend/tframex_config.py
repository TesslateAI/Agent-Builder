# builder/backend/tframex_config.py
import os
import logging
from dotenv import load_dotenv
from tframex import TFrameXApp, OpenAIChatLLM, Tool, setup_logging
from tframex.mcp import MCPManager
import json
from pathlib import Path
from builtin_tools import register_builtin_tools

load_dotenv()

# Setup TFrameX logging
setup_logging(level=logging.INFO, use_colors=True)
logger = logging.getLogger("TFrameXConfig")

# --- Global TFrameX App Instance ---
# This instance will be shared across the backend.
# User-defined agents and tools via the UI will be registered to this instance.
tframex_app_instance: TFrameXApp = None

def init_tframex_app():
    """Initializes and returns the global TFrameXApp instance with v1.1.0 features."""
    global tframex_app_instance
    if tframex_app_instance is not None:
        return tframex_app_instance

    logger.info("Initializing global TFrameXApp instance with v1.1.0 features...")
    
    # Configure the default LLM for the TFrameXApp
    # Support for multiple LLM providers as per v1.1.0
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLAMA_API_KEY")
    api_base_url = os.getenv("OPENAI_API_BASE") or os.getenv("LLAMA_BASE_URL") or "http://localhost:11434/v1"
    model_name = os.getenv("OPENAI_MODEL_NAME") or os.getenv("LLAMA_MODEL") or "llama3.2:1b"
    
    default_llm = OpenAIChatLLM(
        model_name=model_name,
        api_base_url=api_base_url,
        api_key=api_key or "ollama",  # Default for local Ollama
        parse_text_tool_calls=True  # New in v1.1.0 for better tool parsing
    )

    if not default_llm.api_base_url:
        logger.error("FATAL: Default LLM API base URL is not configured.")
    if not default_llm.api_key and "api.openai.com" in str(default_llm.api_base_url):
        logger.error("FATAL: API key is not set for OpenAI LLM.")

    # Check for MCP configuration
    mcp_config_path = os.getenv("MCP_CONFIG_FILE", "servers_config.json")
    if not Path(mcp_config_path).exists():
        logger.info(f"MCP config file {mcp_config_path} not found, MCP features will be disabled")
        mcp_config_path = None

    # Try to detect if we're in an async context for MCP initialization
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        logger.info("Event loop detected, initializing with MCP support")
        use_mcp = mcp_config_path is not None
    except RuntimeError:
        logger.info("No event loop running, deferring MCP initialization")
        use_mcp = False
        # Store MCP config for later initialization
        if mcp_config_path:
            os.environ["TFRAMEX_DEFERRED_MCP_CONFIG"] = mcp_config_path

    # Initialize TFrameXApp with v1.1.0 parameters
    tframex_app_instance = TFrameXApp(
        default_llm=default_llm,
        mcp_config_file=mcp_config_path if use_mcp else None,
        enable_mcp_roots=True,
        enable_mcp_sampling=True,
        enable_mcp_experimental=False,
        mcp_roots_allowed_paths=None  # Can be configured via environment
    )
    
    logger.info(f"TFrameXApp initialized with:")
    logger.info(f"  - LLM: {model_name} via {api_base_url}")
    logger.info(f"  - MCP: {'Enabled' if mcp_config_path else 'Disabled'}")

    # --- Pre-register Example/Core Studio Tools or Agents (Optional) ---
    # Built-in tools are now registered via builtin_tools.py

    # Register example MCP meta-tools if MCP is enabled
    if mcp_config_path and hasattr(tframex_app_instance, '_mcp_manager') and tframex_app_instance._mcp_manager:
        logger.info("MCP is enabled, meta-tools are automatically registered")

    # Two-Agent Architecture: Conversational Assistant + Flow Builder
    
    # 1. Conversational Assistant Agent
    assistant_agent_prompt = """
You are a helpful AI assistant for the TFrameX Agent Builder Studio. You help users design and create visual workflows using TFrameX components.

Your role:
- Have natural conversations with users about their workflow needs
- Ask clarifying questions when needed
- Explain TFrameX concepts and components
- Provide guidance on workflow design
- When the user wants to modify the flow, send instructions to the FlowBuilderAgent

Available TFrameX Components:
{available_components_context}

Current Flow State:
{current_flow_state_context}

Communication Protocol:
- When the user wants to modify the flow, end your response with:
  FLOW_INSTRUCTION: [clear instruction for FlowBuilderAgent]
- Otherwise, respond conversationally to help the user

Be helpful, friendly, and educational. Help users understand how to build effective workflows with TFrameX.
    """
    
    @tframex_app_instance.agent(
        name="ConversationalAssistant",
        description="Friendly assistant that talks to users about their workflow needs and coordinates with the FlowBuilderAgent.",
        system_prompt=assistant_agent_prompt,
        strip_think_tags=True
    )
    async def _conversational_assistant_placeholder():
        pass
    
    # 2. Flow Builder Agent (receives instructions from assistant)
    flow_builder_agent_prompt = """
You are a specialized agent that converts workflow instructions into ReactFlow JSON for TFrameX components.

Your role:
- Receive clear instructions from the OrchestratorAgent
- Generate precise ReactFlow JSON based on those instructions
- Consider the current flow state and available components
- Output clean, valid JSON that can be parsed directly

Available TFrameX Components:
{available_components_context}

Current Flow State:
{current_flow_state_context}

Instruction: {flow_instruction}

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON - no markdown, no explanations, no extra text
2. JSON must have "nodes" and "edges" keys - NEVER empty edges array
3. Node 'type' must be EXACT TFrameX component ID from the available components list above
4. For AGENT nodes: type must be an agent ID like "ConversationalAssistant", "OrchestratorAgent"
5. For TOOL nodes: type must be an exact tool ID like "HTTP Request Tool", "Web Search Tool", "Text Pattern Matcher"
6. For PATTERN nodes: type must be pattern class name like "SequentialPattern", "ParallelPattern"
7. Agent nodes should have data.component_category = "agent"
8. Tool nodes should have data.component_category = "tool" 
9. Pattern nodes should have data.component_category = "pattern"
10. ALWAYS generate edges connecting tools to agents 
11. Simple edges need only: id, source, target (ReactFlow handles the rest automatically)
12. NEVER generate empty edges array - always connect the components you create

POSITIONING: Use LEFT-TO-RIGHT flow layout:
- Input tools on the LEFT at x=50, spread vertically at y=100, y=200, etc.
- Agent in the CENTER at x=300, y=150
- Output elements on the RIGHT at x=550+ if needed

EDGE HANDLES: Use proper ReactFlow handles for tool-to-agent connections:
- Tools connect TO agents with NO handles specified (ReactFlow auto-connects)
- Flow sequence uses sourceHandle/targetHandle for specific connections

FLOW PATTERN EXAMPLES:

1. AGENT-TO-TOOLS PATTERN:
{
  "nodes": [
    {"id": "tool1", "type": "HTTP Request Tool", "data": {"label": "HTTP Request Tool", "component_category": "tool"}, "position": {"x": 50, "y": 100}},
    {"id": "agent1", "type": "ConversationalAssistant", "data": {"label": "Processing Agent", "component_category": "agent"}, "position": {"x": 300, "y": 150}}
  ],
  "edges": [{"id": "edge1", "source": "tool1", "target": "agent1"}]
}

2. AGENT-TO-AGENT SEQUENTIAL FLOW:
{
  "nodes": [
    {"id": "agent1", "type": "ConversationalAssistant", "data": {"label": "Prompt Creator", "component_category": "agent"}, "position": {"x": 50, "y": 150}},
    {"id": "agent2", "type": "ConversationalAssistant", "data": {"label": "Response Agent", "component_category": "agent"}, "position": {"x": 300, "y": 150}}
  ],
  "edges": [
    {"id": "edge1", "source": "agent1", "target": "agent2"}
  ]
}

3. PARALLEL AGENTS WITH PATTERN:
{
  "nodes": [
    {"id": "agent1", "type": "ConversationalAssistant", "data": {"label": "Agent 1", "component_category": "agent"}, "position": {"x": 50, "y": 100}},
    {"id": "agent2", "type": "ConversationalAssistant", "data": {"label": "Agent 2", "component_category": "agent"}, "position": {"x": 50, "y": 200}},
    {"id": "pattern1", "type": "ParallelPattern", "data": {"label": "Parallel Execution", "component_category": "pattern", "tasks": ["agent1", "agent2"]}, "position": {"x": 300, "y": 150}}
  ],
  "edges": [
    {"id": "edge1", "source": "agent1", "target": "pattern1"},
    {"id": "edge2", "source": "agent2", "target": "pattern1"}
  ]
}

CHOOSE THE RIGHT PATTERN based on the user's request - don't just copy examples!

Output the JSON now:
    """
    
    @tframex_app_instance.agent(
        name="FlowBuilderAgent",
        description="Specialized agent that generates ReactFlow JSON based on instructions from the ConversationalAssistant.",
        system_prompt=flow_builder_agent_prompt,
        strip_think_tags=True
    )
    async def _flow_builder_agent_placeholder():
        pass

    # 3. Orchestrator Agent (coordinates flow building with tool calling)
    orchestrator_agent_prompt = """
You are the OrchestratorAgent for the TFrameX Agent Builder Studio. You are the PRIMARY interface for users building workflows. You handle conversations, analyze flows, and coordinate with FlowBuilderAgent to create visual flows.

Your core capabilities:
- Have natural conversations with users about their workflow needs
- Analyze existing flows using specialized tools
- Predict optimal next components to add
- Coordinate with FlowBuilderAgent to generate ReactFlow JSON
- Provide intelligent suggestions and explanations

Available Tools:
{available_tools_descriptions}

Current Flow State:
{current_flow_state_context}

Available Components:
{available_components_context}

Your conversational approach:
1. LISTEN CAREFULLY: Focus on the USER'S specific request, not preset examples
2. ANALYZE THE REQUEST: Use your Drag-Drop Predictor tool to understand what the user actually wants
3. IDENTIFY FLOW PATTERN: Determine if this is agent-to-agent, agent-to-tools, or pattern-based flow
4. BUILD APPROPRIATELY: Create the flow that matches the user's actual need

Communication Protocol for Flow Modifications:
- ALWAYS use your analysis tools to understand the user's specific request
- DO NOT copy examples - analyze what the user actually wants
- When the user wants to add, modify, or create flow components, end your response with:
  FLOW_INSTRUCTION: [clear instruction for FlowBuilderAgent based on YOUR analysis]

FLOW PATTERN RECOGNITION:
- "agent creates X and outputs to another agent" = Sequential agent-to-agent flow with SequentialPattern
- "agent processes files/data" = Agent with appropriate tools (File Reader, etc.)
- "multiple agents work together" = Coordination pattern (Sequential, Parallel, Discussion)
- "route between different agents" = RouterPattern
- "agents discuss/collaborate" = DiscussionPattern

CRITICAL: Use your Drag-Drop Predictor tool to analyze each request. Do not assume or copy examples.

Example approach:
User: [ANY REQUEST]
You: "Let me analyze your request using my tools to understand exactly what you need. [Use Drag-Drop Predictor with user intent] Based on my analysis of your specific request, I can see you want [specific analysis result]. Let me create this for you.

FLOW_INSTRUCTION: [Instruction based on YOUR analysis, not examples]"

REMEMBER: Every user request is unique. Use your tools to analyze what they actually want.

Be helpful, conversational, and use your analytical tools to provide intelligent guidance.
    """
    
    @tframex_app_instance.agent(
        name="OrchestratorAgent",
        description="Coordinates flow building activities with tool calling for analysis, prediction, and optimization.",
        system_prompt=orchestrator_agent_prompt,
        strip_think_tags=True,
        can_use_tools=True,
        tool_names=["Flow Structure Analyzer", "Drag-Drop Predictor", "Flow Optimizer", "Math Calculator", "Text Pattern Matcher"]
    )
    async def _orchestrator_agent_placeholder():
        pass

    logger.info("ConversationalAssistant, FlowBuilderAgent, and OrchestratorAgent registered.")
    
    # Register built-in tools
    try:
        register_builtin_tools(tframex_app_instance)
        logger.info("Built-in tools registered successfully.")
    except Exception as e:
        logger.error(f"Failed to register built-in tools: {e}")
    
    return tframex_app_instance

async def init_deferred_mcp() -> bool:
    """Initialize MCP if it was deferred due to missing event loop."""
    global tframex_app_instance
    
    if tframex_app_instance is None:
        logger.warning("Cannot initialize MCP: TFrameX app not initialized")
        return False
    
    # Check if MCP is already initialized
    if hasattr(tframex_app_instance, '_mcp_manager') and tframex_app_instance._mcp_manager:
        logger.info("MCP already initialized")
        return True
    
    # Check for deferred MCP config
    deferred_config = os.getenv("TFRAMEX_DEFERRED_MCP_CONFIG")
    if not deferred_config:
        logger.info("No deferred MCP config found")
        return False
    
    if not Path(deferred_config).exists():
        logger.warning(f"Deferred MCP config file not found: {deferred_config}")
        return False
    
    try:
        from tframex.mcp import MCPManager
        logger.info(f"Initializing deferred MCP with config: {deferred_config}")
        
        tframex_app_instance._mcp_manager = MCPManager(
            mcp_config_file_path=deferred_config,
            default_llm=tframex_app_instance.default_llm,
            enable_roots=True,
            enable_sampling=True,
            enable_experimental=False,
            roots_allowed_paths=None
        )
        
        logger.info("Deferred MCP initialization successful")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize deferred MCP: {e}")
        return False

def get_tframex_app_instance() -> TFrameXApp:
    """Returns the initialized global TFrameX App instance with lazy initialization."""
    global tframex_app_instance
    if tframex_app_instance is None:
        logger.info("Lazy initializing TFrameX app instance...")
        tframex_app_instance = init_tframex_app()
    return tframex_app_instance