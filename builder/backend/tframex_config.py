# builder/backend/tframex_config.py
import os
import logging
from dotenv import load_dotenv
from tframex import TFrameXApp, OpenAIChatLLM, Tool, setup_logging
from tframex.mcp import MCPManager
import json
from pathlib import Path

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
    model_name = os.getenv("OPENAI_MODEL_NAME") or os.getenv("LLAMA_MODEL") or "gpt-3.5-turbo"
    
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

    # Initialize TFrameXApp with v1.1.0 parameters
    tframex_app_instance = TFrameXApp(
        default_llm=default_llm,
        mcp_config_file=mcp_config_path,
        enable_mcp_roots=True,
        enable_mcp_sampling=True,
        enable_mcp_experimental=False,
        mcp_roots_allowed_paths=None  # Can be configured via environment
    )
    
    logger.info(f"TFrameXApp initialized with:")
    logger.info(f"  - LLM: {model_name} via {api_base_url}")
    logger.info(f"  - MCP: {'Enabled' if mcp_config_path else 'Disabled'}")

    # --- Pre-register Example/Core Studio Tools or Agents (Optional) ---
    # Example: A simple tool available by default
    @tframex_app_instance.tool(name="studio_example_tool", description="A sample tool provided by the Studio.")
    async def _studio_example_tool(text: str) -> str:
        logger.info(f"Studio Example Tool called with: {text}")
        return f"Studio Example Tool processed: '{text.upper()}'"

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
- Receive clear instructions from the ConversationalAssistant
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
2. JSON must have "nodes" and "edges" keys
3. Node 'type' must be valid TFrameX component ID
4. Agent nodes can have 'label', 'selected_tools', 'template_vars_config' in data
5. Pattern nodes must have proper constructor parameters in data
6. Generate appropriate positions for new nodes

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

    logger.info("ConversationalAssistant and FlowBuilderAgent registered.")
    return tframex_app_instance

# Ensure it's initialized when this module is imported
if tframex_app_instance is None:
    tframex_app_instance = init_tframex_app()

def get_tframex_app_instance() -> TFrameXApp:
    """Returns the initialized global TFrameXApp instance."""
    if tframex_app_instance is None:
        # This case should ideally not be hit if init_tframex_app() is called on module load
        logger.warning("get_tframex_app_instance called before initialization. Initializing now.")
        return init_tframex_app()
    return tframex_app_instance