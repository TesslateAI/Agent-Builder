# builder/backend/tframex_config.py
import os
import logging
from dotenv import load_dotenv
from tframex import TFrameXApp, OpenAIChatLLM, Tool # Import Tool for potential pre-registration

load_dotenv()
logger = logging.getLogger("TFrameXConfig")

# --- Global TFrameX App Instance ---
# This instance will be shared across the backend.
# User-defined agents and tools via the UI will be registered to this instance.
tframex_app_instance: TFrameXApp = None

def init_tframex_app():
    """Initializes and returns the global TFrameXApp instance."""
    global tframex_app_instance
    if tframex_app_instance is not None:
        return tframex_app_instance

    logger.info("Initializing global TFrameXApp instance...")
    
    # Configure the default LLM for the TFrameXApp
    # This LLM will be used by agents unless they have a specific override
    default_llm = OpenAIChatLLM(
        model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
        api_base_url=os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1"), # Default for local Ollama
        api_key=os.getenv("OPENAI_API_KEY", "ollama") # Default for local Ollama
    )

    if not default_llm.api_base_url:
        logger.error("FATAL: Default LLM API base URL (OPENAI_API_BASE) is not configured.")
        # In a real app, you might raise an exception or prevent startup
    if not default_llm.api_key and default_llm.api_base_url and "api.openai.com" in default_llm.api_base_url:
         logger.error("FATAL: OPENAI_API_KEY is not set for OpenAI default LLM.")


    tframex_app_instance = TFrameXApp(default_llm=default_llm)
    logger.info(f"TFrameXApp initialized with default LLM: {default_llm.model_id if default_llm else 'None'}")

    # --- Pre-register Example/Core Studio Tools or Agents (Optional) ---
    # Example: A simple tool available by default
    @tframex_app_instance.tool(name="studio_example_tool", description="A sample tool provided by the Studio.")
    async def _studio_example_tool(text: str) -> str:
        logger.info(f"Studio Example Tool called with: {text}")
        return f"Studio Example Tool processed: '{text.upper()}'"

    # Example: A default agent for the chatbot flow builder (if needed)
    # This agent's prompt needs to be VERY carefully crafted to output ReactFlow JSON
    studio_flow_builder_agent_prompt = """
You are an AI assistant that helps users design visual workflows using TFrameX components by outputting ReactFlow JSON.
Based on the user's request, the available TFrameX components, and the current flow state,
you must generate a complete JSON object representing the new visual flow.

Output *only* a valid JSON object with "nodes" and "edges" keys.
- "nodes": Array of node objects (id, type, position, data).
  - 'type' must be a valid TFrameX component ID (e.g., an agent name, or a Pattern class name like 'SequentialPattern').
  - 'data' for Agent nodes can include 'label', 'selected_tools' (list of tool names), 'template_vars_config' (dict).
  - 'data' for Pattern nodes must include parameters for their constructor (e.g., for SequentialPattern: 'steps_config': ['AgentName1', 'AgentName2']). Agent names in pattern configs must be valid.
- "edges": Array of edge objects (id, source, target, sourceHandle, targetHandle).

Available TFrameX Components:
{available_components_context}

Current Flow State:
{current_flow_state_context}

User's Request: {user_query}

Think step-by-step using <think>...</think> tags.
The final output MUST be ONLY the JSON object.
    """
    @tframex_app_instance.agent(
        name="StudioFlowBuilderMetaAgent",
        description="Internal agent used by the Studio chatbot to generate ReactFlow JSON for TFrameX flows.",
        system_prompt=studio_flow_builder_agent_prompt,
        strip_think_tags=True # Important for clean JSON output
    )
    async def _studio_flow_builder_meta_agent_placeholder():
        pass # Logic is handled by TFrameX LLMAgent

    logger.info("StudioFlowBuilderMetaAgent registered.")
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