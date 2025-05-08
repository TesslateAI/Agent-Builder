# backend/agents/flow_builder.py
import logging
import json
from tframex.agents import BasicAgent # Use BasicAgent for the underlying call

logger = logging.getLogger(__name__)

# --- Helper to create the prompt ---
def create_flow_builder_prompt(user_request: str, available_nodes_str: str, current_flow_str: str) -> str:
    """Creates the detailed prompt for the LLM flow builder agent."""

    # Define the expected JSON output format explicitly in the prompt
    json_format_description = """
    /no_think
Your goal is to understand the user's request and generate an updated flow configuration consisting of nodes and edges.
You MUST output a valid JSON object *after* your thinking process (outside the <think> tags).
The JSON object MUST have the following structure:
{
  "nodes": [
    {
      "id": "unique_node_id_string",
      "type": "node_type_string", // Must be ONLY one of the available node types
      "position": {"x": number, "y": number}, // Approximate position is fine
      "data": { ... } // An object containing node-specific data (like prompt, context, userRequest etc.)
    }
    // ... more node objects
  ],
  "edges": [
    {
      "id": "unique_edge_id_string", // e.g., "reactflow__edge-node1output_out-node2input_in"
      "source": "source_node_id_string",
      "target": "target_node_id_string",
      "sourceHandle": "source_handle_id_string", // e.g., "output_out"
      "targetHandle": "target_handle_id_string" // e.g., "context_in"
      // Optional: "type": "smoothstep", "animated": true
    }
    // ... more edge objects
  ]
}

Example Node data content based on type:
- basicAgent: {"label": "Agent Name", "prompt": "User prompt here", "max_tokens": null}
- contextAgent: {"label": "Agent Name", "prompt": "User prompt", "context": "Context text", "max_tokens": null}
- chainOfAgents: {"label": "System Name", "initialPrompt": "...", "longText": "...", "maxTokens": null, "chunkSize": 2000, "chunkOverlap": 200}
- multiCallSystem: {"label": "System Name", "prompt": "...", "numCalls": 5, "baseFilename": "output", "maxTokens": 1000}

Example JSON for a website:
{
  "nodes": [
    {
      "id": "planner-1", // ID can vary
      "type": "plannerAgent", // Must match agent_definitions.py
      "position": { "x": 100, "y": 150 }, // Example position
      "data": {
        "label": "Plan Software", // Optional label
        "user_request": "" // Planner node needs this field, initially empty
      }
    },
    {
      "id": "distributor-1", // ID can vary
      "type": "distributorAgent", // Must match agent_definitions.py
      "position": { "x": 400, "y": 150 }, // Example position
      "data": {
        "label": "Distribute Tasks" // Optional label
      }
    },
    {
      "id": "generator-1", // ID can vary
      "type": "fileGeneratorAgent", // Must match agent_definitions.py
      "position": { "x": 700, "y": 150 }, // Example position
      "data": {
        "label": "Generate Files" // Optional label
        // Note: run_id is NOT set here, it's added by the executor
      }
    }
  ],
  "edges": [
    {
      "id": "reactflow__edge-planner-1plan_out-distributor-1plan_in", // ID format convention
      "source": "planner-1",
      "target": "distributor-1",
      "sourceHandle": "plan_out", // Matches plannerAgent output handle
      "targetHandle": "plan_in", // Matches distributorAgent input handle
      "type": "smoothstep", // Optional styling
      "animated": true      // Optional styling
    },
    // Edge for Memory output -> input
    {
      "id": "reactflow__edge-distributor-1memory_out-generator-1memory_in",
      "source": "distributor-1",
      "target": "generator-1",
      "sourceHandle": "memory_out", // Matches distributorAgent output handle
      "targetHandle": "memory_in", // Matches fileGeneratorAgent input handle
      "type": "smoothstep",
      "animated": true
    },
    // Edge for File Prompts output -> input
    {
      "id": "reactflow__edge-distributor-1file_prompts_out-generator-1file_prompts_in",
      "source": "distributor-1",
      "target": "generator-1",
      "sourceHandle": "file_prompts_out", // Matches distributorAgent output handle
      "targetHandle": "file_prompts_in", // Matches fileGeneratorAgent input handle
      "type": "smoothstep",
      "animated": true
    }
  ]
}

IMPORTANT:
- Base your response ENTIRELY on the user's request and the provided context (available nodes, current flow).
- If the user asks to modify the flow, output the *complete* new JSON structure for the *entire* flow, not just the changes.
- If the user asks to create a new flow, generate appropriate node IDs and edge IDs.
- Ensure `type` in nodes matches one of the available node types.
- Ensure `sourceHandle` and `targetHandle` in edges correspond logically to the node types involved (use the available node info for guidance).
- Place nodes at reasonable default positions (e.g., incrementing x for sequential nodes).
- Output *only* the JSON object after the </think> tag. Do not include explanations before or after the JSON.
"""

    prompt = f"""
You are an expert assistant helping a user build automation flows using a visual editor.
Your task is to generate or modify a flow based on the user's request.

<CONTEXT>
Available Node Types:
--- AVAILABLE NODES START ---
{available_nodes_str}
--- AVAILABLE NODES END ---

Current Flow State (Nodes and Edges):
--- CURRENT FLOW START ---
{current_flow_str}
--- CURRENT FLOW END ---
</CONTEXT>

<USER_REQUEST>
{user_request}
</USER_REQUEST>

<INSTRUCTIONS>
{json_format_description}
</INSTRUCTIONS>

<TASK>
First, think step-by-step within <think></think> tags about how to fulfill the user request based on the context and instructions. Analyze the request, determine the necessary nodes, their connections (edges), and required data. Consider the existing flow if modifications are requested.
After your thinking process, output the *complete* JSON object representing the desired final flow state (nodes and edges).
</TASK>
"""
    return prompt

# --- Execution Function ---
async def execute_flow_builder_agent(agent_instance: BasicAgent, input_data: dict) -> dict:
    """
    Executes the Flow Builder Agent logic.
    Input data expected: {
        'user_message': str,
        'available_nodes_context': str,
        'current_flow_context': str
    }
    Output data: {'raw_llm_output': str} # Return the raw output including <think> tags
    """
    user_message = input_data.get('user_message')
    available_nodes_context = input_data.get('available_nodes_context', 'No node definitions provided.')
    current_flow_context = input_data.get('current_flow_context', '{"nodes": [], "edges": []}') # Default to empty flow

    if not user_message:
        logger.error("FlowBuilderAgent execution failed: 'user_message' input is missing.")
        # Return raw output indicating error, the API handler will parse/handle this
        return {"raw_llm_output": "<think>Error: User message was empty.</think>"}

    # Construct the detailed prompt
    prompt = create_flow_builder_prompt(user_message, available_nodes_context, current_flow_context)

    logger.info(f"Running FlowBuilderAgent for user message: '{user_message[:100]}...'")
    try:
        # Use the underlying BasicAgent's run method
        # Use a high max_tokens as the JSON + context can be large
        response = await agent_instance.run(prompt=prompt, max_tokens=8000, temperature=0.3) # Lower temp for more predictable JSON
        # Return the raw response directly
        return {"raw_llm_output": response}
    except Exception as e:
        logger.error(f"FlowBuilderAgent execution encountered an error: {e}", exc_info=True)
        # Return raw output indicating error
        return {"raw_llm_output": f"<think>Error during LLM call: {e}</think>"}