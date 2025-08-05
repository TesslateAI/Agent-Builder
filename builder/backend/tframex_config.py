# builder/backend/tframex_config.py
import os
import logging
from dotenv import load_dotenv
from tframex import TFrameXApp, OpenAIChatLLM, setup_logging
from pathlib import Path
from builtin_tools import register_builtin_tools
from agents import register_conversational_assistant, register_flow_builder_agent, register_orchestrator_agent, register_research_agent

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
        asyncio.get_running_loop()
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
    
    logger.info("TFrameXApp initialized with:")
    logger.info(f"  - LLM: {model_name} via {api_base_url}")
    logger.info(f"  - MCP: {'Enabled' if mcp_config_path else 'Disabled'}")

    # --- Pre-register Example/Core Studio Tools or Agents (Optional) ---
    # Built-in tools are now registered via builtin_tools.py

    # Register example MCP meta-tools if MCP is enabled
    if mcp_config_path and hasattr(tframex_app_instance, '_mcp_manager') and tframex_app_instance._mcp_manager:
        logger.info("MCP is enabled, meta-tools are automatically registered")

    # Register agents
    register_conversational_assistant(tframex_app_instance)
    register_flow_builder_agent(tframex_app_instance)
    register_orchestrator_agent(tframex_app_instance)
    register_research_agent(tframex_app_instance)
    logger.info("ConversationalAssistant, FlowBuilderAgent, OrchestratorAgent, and ResearchAgent registered.")
    
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