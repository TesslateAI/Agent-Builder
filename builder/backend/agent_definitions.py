# builder/backend/agent_definitions.py
import os
import logging
from dotenv import load_dotenv

# Import tframex components needed for instantiation
from tframex.model import VLLMModel
from tframex.agents import BasicAgent, ContextAgent # BasicAgent is needed for FlowBuilder and others
from tframex.systems import ChainOfAgents, MultiCallSystem

# Import the execution functions
from agents.basic import execute_basic_agent
from agents.context import execute_context_agent
from agents.chain import execute_chain_system
from agents.multi_call import execute_multi_call_system
from agents.flow_builder import execute_flow_builder_agent
# --- NEW AGENT IMPORTS ---
from agents.planner_agent import execute_planner_agent
from agents.distributor_agent import execute_distributor_agent
from agents.file_generator_agent import execute_file_generator_agent
from agents.prompt_injector_agent import execute_prompt_injector_agent # ADD THIS LINE
# --- END NEW AGENT IMPORTS ---


load_dotenv()
logger = logging.getLogger(__name__)

# --- Configs (remain the same) ---
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS", 32000))
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
MULTI_CALL_OUTPUT_DIR = os.getenv("MULTI_CALL_OUTPUT_DIR", "example_outputs/ex4_multi_call_outputs")
CHAIN_CHUNK_SIZE = int(os.getenv("CHAIN_CHUNK_SIZE", 2000))
CHAIN_CHUNK_OVERLAP = int(os.getenv("CHAIN_CHUNK_OVERLAP", 200))
# Note: Add specific configs for new agents if needed (e.g., output directories)
# Example: SOFTWARE_OUTPUT_DIR = os.getenv("SOFTWARE_OUTPUT_DIR", "generated_software")

# --- Agent/System Definition Registry ---
AGENT_REGISTRY = {}

def register_agent(agent_id, name, description, agent_type, inputs, outputs, constructor, execute_function):
    """Helper to register agent/system definitions."""
    if agent_id in AGENT_REGISTRY:
        logger.warning(f"Agent/System with ID '{agent_id}' is being re-registered.")

    # Basic validation (Improved version allowing description-only inputs/outputs)
    for logical_name, details in inputs.items():
         if not isinstance(details, dict) or ('handle_id' not in details and 'description' not in details): # Allow description only
             raise ValueError(f"Input '{logical_name}' for agent '{agent_id}' lacks required 'description' key (and potentially 'handle_id').")
         # Add more specific validation if needed (e.g., type, required)
         if not details.get("description"):
             raise ValueError(f"Input '{logical_name}' for agent '{agent_id}' must have a 'description'.")

    for logical_name, details in outputs.items():
        if not isinstance(details, dict) or ('handle_id' not in details and 'description' not in details): # Allow description only
             raise ValueError(f"Output '{logical_name}' for agent '{agent_id}' lacks required 'description' key (and potentially 'handle_id').")
        if not details.get("description"):
             raise ValueError(f"Output '{logical_name}' for agent '{agent_id}' must have a 'description'.")

    AGENT_REGISTRY[agent_id] = {
        "id": agent_id,
        "name": name,
        "description": description,
        "type": agent_type,
        "inputs": inputs,
        "outputs": outputs,
        "constructor": constructor,
        "execute_function": execute_function
    }
    logger.debug(f"Registered agent/system: {agent_id}")

# --- Define Existing Agents/Systems with Explicit Handles ---

# Basic Agent
register_agent(
    agent_id="basicAgent",
    name="Basic Agent",
    description="A simple agent that takes a prompt and returns a response.",
    agent_type="agent",
    inputs={
        "prompt": {
            "handle_id": "prompt_in",
            "description": "The main instruction or question.",
            "required": True,
            "type": "string"
        },
        "max_tokens": {
            "handle_id": "max_tokens_in",
            "description": "(Optional) Max tokens for the response.",
            "required": False,
            "type": "integer"
        }
    },
    outputs={
        "output": {
            "handle_id": "output_out",
            "description": "The generated response text.",
            "type": "string"
        }
    },
    constructor=lambda model: BasicAgent(agent_id="dynamic_basic", model=model),
    execute_function=execute_basic_agent
)

# Context Agent
register_agent(
    agent_id="contextAgent",
    name="Context Agent",
    description="An agent that considers provided context along with the prompt.",
    agent_type="agent",
    inputs={
        "prompt": {
            "handle_id": "prompt_in",
            "description": "The main instruction or question.",
            "required": True,
            "type": "string"
        },
        "context": {
            "handle_id": "context_in",
            "description": "Background text or information.",
            "required": True, # Make context required if passed via edge usually
            "type": "string"
        },
        "max_tokens": {
            "handle_id": "max_tokens_in",
            "description": "(Optional) Max tokens for the response.",
            "required": False,
            "type": "integer"
        }
    },
    outputs={
        "output": {
            "handle_id": "output_out",
            "description": "The generated response text.",
            "type": "string"
        }
    },
    constructor=lambda model: ContextAgent(agent_id="dynamic_context", model=model, context=""), # Default context empty
    execute_function=execute_context_agent
)

# Chain of Agents System
register_agent(
    agent_id="chainOfAgents",
    name="Chain of Agents",
    description="Summarizes or answers questions about long text by processing it in chunks.",
    agent_type="system",
    inputs={
        "initial_prompt": {
            "handle_id": "prompt_in",
            "description": "The prompt guiding the overall task.",
            "required": True,
            "type": "string"
        },
        "long_text": {
            "handle_id": "text_in",
            "description": "The long document to process.",
            "required": True,
            "type": "string"
        },
        "max_tokens": {
            "handle_id": "max_tokens_in",
            "description": "(Optional) Max tokens for the final combined response.",
            "required": False,
            "type": "integer"
        }
        # Note: chunk_size, chunk_overlap are configured via constructor, not input handles
    },
    outputs={
        "output": {
            "handle_id": "output_out",
            "description": "The final combined response.",
            "type": "string"
        }
    },
    constructor=lambda model: ChainOfAgents(
        system_id="dynamic_chain",
        model=model,
        chunk_size=CHAIN_CHUNK_SIZE,
        chunk_overlap=CHAIN_CHUNK_OVERLAP
    ),
    execute_function=execute_chain_system
)

# Multi Call System
register_agent(
    agent_id="multiCallSystem",
    name="Multi Call System",
    description="Runs the same prompt multiple times concurrently, saving outputs.",
    agent_type="system",
    inputs={
        "prompt": {
            "handle_id": "prompt_in",
            "description": "The prompt to run multiple times.",
            "required": True,
            "type": "string"
        },
        "num_calls": {
            "handle_id": "num_calls_in",
            "description": "Number of concurrent calls (default: 3).",
            "required": False,
            "type": "integer"
        },
        "base_filename": {
            "handle_id": "filename_in",
            "description": "Base name for output files (default: multi_output).",
            "required": False,
            "type": "string"
        },
        "max_tokens": {
            "handle_id": "max_tokens_in",
            "description": "(Optional) Max tokens for each individual call's response.",
            "required": False,
            "type": "integer"
        }
        # Note: output_dir is configured via constructor
    },
    outputs={
        "output": { # The summary log is the primary output here
            "handle_id": "output_out",
            "description": "A summary log of the file paths or errors.",
            "type": "string"
        }
    },
    constructor=lambda model: MultiCallSystem(
        system_id="dynamic_multi",
        model=model,
        default_output_dir=MULTI_CALL_OUTPUT_DIR
    ),
    execute_function=execute_multi_call_system
)

# Flow Builder Agent (Internal)
register_agent(
    agent_id="flowBuilderAgent",
    name="Flow Builder Agent",
    description="Internal agent used by the chatbot sidebar to generate/modify flows.",
    agent_type="agent", # It acts like an agent taking instructions
    inputs={
        # These inputs are not visual handles, just logical data for the execution function
        "user_message": {"description": "The natural language request from the user.", "required": True, "type": "string"},
        "available_nodes_context": {"description": "String describing available node types.", "required": True, "type": "string"},
        "current_flow_context": {"description": "JSON string of the current nodes and edges.", "required": True, "type": "string"}
    },
    outputs={
        # This output is not a visual handle, it's the raw result for the API handler
        "raw_llm_output": {"description": "The raw output from the LLM, potentially including <think> tags and JSON.", "type": "string"}
    },
    # Use a BasicAgent instance as the underlying executor for the complex prompt
    constructor=lambda model: BasicAgent(agent_id="dynamic_flowbuilder", model=model),
    execute_function=execute_flow_builder_agent
)


# --- NEW: Software Builder Agents Registration ---

# 1. Planner Agent
register_agent(
    agent_id="plannerAgent",
    name="Software: Planner",
    description="Takes a user request and generates a detailed development plan.",
    agent_type="agent",
    inputs={
        "user_request": {
            "handle_id": "user_request_in",
            "description": "The high-level user request for the software.",
            "required": True,
            "type": "string"
        }
        # Optional max_tokens can be added if needed
    },
    outputs={
        "plan": {
            "handle_id": "plan_out",
            "description": "The detailed development plan (markdown).",
            "type": "string"
        }
    },
    # Use BasicAgent instance as executor, could also be custom class inheriting BaseAgent
    constructor=lambda model: BasicAgent(agent_id="dynamic_planner", model=model),
    execute_function=execute_planner_agent
)

# 2. Distributor Agent
register_agent(
    agent_id="distributorAgent",
    name="Software: Distributor",
    description="Breaks a development plan into shared memory and specific file prompts.",
    agent_type="agent",
    inputs={
        "plan": {
            "handle_id": "plan_in",
            "description": "The development plan generated by the Planner.",
            "required": True,
            "type": "string"
        }
    },
    outputs={
        "memory": {
            "handle_id": "memory_out",
            "description": "Shared context for file generation.",
            "type": "string"
        },
        "file_prompts_json": {
            "handle_id": "file_prompts_out",
            "description": "JSON string containing a list of file generation prompts.",
            "type": "string"
        }
    },
    constructor=lambda model: BasicAgent(agent_id="dynamic_distributor", model=model),
    execute_function=execute_distributor_agent
)

# 3. File Generator Agent
register_agent(
    agent_id="fileGeneratorAgent",
    name="Software: File Generator",
    description="Generates code files based on prompts and memory, saves them.",
    agent_type="agent", # Acts as one step, despite internal concurrency
    inputs={
        "memory": {
            "handle_id": "memory_in",
            "description": "Shared context from the Distributor.",
            "required": True,
            "type": "string"
        },
        "file_prompts_json": {
            "handle_id": "file_prompts_in",
            "description": "JSON string of file prompts from the Distributor.",
            "required": True,
            "type": "string"
        },
        # This input is special, provided by the executor, not an edge usually
        "run_id": {
            "description": "Unique ID for the current run (set by executor).",
            "required": True, # Technically required by the execution function
            "type": "string",
            # No handle_id as it's not meant for visual connection
        }
    },
    outputs={
        "generation_summary": {
            "handle_id": "summary_out",
            "description": "A log summarizing file generation success/failure.",
            "type": "string"
        },
        "preview_link": {
            "handle_id": "preview_link_out",
            "description": "Relative URL path to preview the generated site (e.g., /api/preview/run_xyz/index.html).",
            "type": "string"
        }
    },
    # Although it uses multiple calls internally, the constructor can still be simple
    # The complexity is handled within its execute_function
    constructor=lambda model: BasicAgent(agent_id="dynamic_generator", model=model),
    execute_function=execute_file_generator_agent
)

# --- NEW: Prompt Injector Agent Registration ---
register_agent(
    agent_id="promptInjectorAgent",
    name="Prompt Injector",
    description="Manually input a combined memory and file prompts block. Splits into memory and file prompts data for FileGenerator.",
    agent_type="agent",
    inputs={
        "full_prompt": { # This is NOT an edge input, it's a data field.
            "description": "The full text containing <memory>...</memory> and <prompt filename='...'>...</prompt> blocks.",
            "required": True,
            "type": "string"
            # No 'handle_id'
        }
    },
    outputs={
        "memory": {
            "handle_id": "memory_out", # This IS an edge output.
            "description": "Shared memory context extracted from the input.",
            "type": "string"
        },
        "file_prompts_json": {
            "handle_id": "file_prompts_out", # This IS an edge output.
            "description": "JSON string of file generation prompts extracted from the input.",
            "type": "string"
        }
    },
    constructor=lambda model: BasicAgent(agent_id="dynamic_promptinjector", model=model), # Simple constructor, no LLM needed here.
    execute_function=execute_prompt_injector_agent
)

# --- END NEW AGENT REGISTRATION ---


# --- END NEW AGENT REGISTRATION ---


# --- Functions to Access Definitions ---
def get_definitions_for_frontend():
    """Returns a list of definitions suitable for the frontend node list."""
    frontend_definitions = []
    # Exclude internal agents like flowBuilderAgent from the node list
    excluded_ids = {"flowBuilderAgent"}
    for agent_id, definition in AGENT_REGISTRY.items():
        if agent_id in excluded_ids:
            continue

        # Filter inputs/outputs to only include those with a visual handle_id
        inputs_for_frontend = {
            lname: details.get("description", "")
            for lname, details in definition.get("inputs", {}).items()
            if details.get("handle_id")
        }
        outputs_for_frontend = {
            lname: details.get("description", "")
            for lname, details in definition.get("outputs", {}).items()
            if details.get("handle_id")
        }
        input_handles = {
            lname: details["handle_id"]
            for lname, details in definition.get("inputs", {}).items()
            if details.get("handle_id")
        }
        output_handles = {
            lname: details["handle_id"]
            for lname, details in definition.get("outputs", {}).items()
            if details.get("handle_id")
        }

        frontend_definitions.append({
            "id": definition["id"],
            "name": definition["name"],
            "description": definition.get("description", ""),
            "type": definition.get("type", "unknown"),
            "inputs": inputs_for_frontend,
            "outputs": outputs_for_frontend,
            "input_handles": input_handles,
            "output_handles": output_handles,
        })
    return frontend_definitions

def get_definition(agent_id):
    """Returns the full internal definition for an agent ID."""
    return AGENT_REGISTRY.get(agent_id)

logger.info(f"Agent Registry loaded with {len(AGENT_REGISTRY)} definitions.")