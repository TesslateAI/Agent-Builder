# builder/backend/flow_executor.py
import asyncio
import os
import logging
import time
import re # Import re for stripping tags
from typing import List, Dict, Any, Set, Optional, Tuple
from collections import deque, defaultdict
from dotenv import load_dotenv

# Import agent definitions and model setup
from agent_definitions import get_definition # Import only the getter
from tframex.model import VLLMModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FlowExecutor")

# --- Model Setup (Keep existing get_model logic) ---
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS", 32000))
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

vllm_model_instance: Optional[VLLMModel] = None
model_lock = asyncio.Lock()

async def get_model() -> VLLMModel:
    # Keep existing get_model logic...
    global vllm_model_instance
    async with model_lock:
        if vllm_model_instance is None:
            logger.info("Initializing VLLM Model instance...")
            try:
                # --- Add helper method if not using BasicAgent ---
                async def _stream_and_aggregate_helper(model, messages, **kwargs):
                    full_response = ""
                    async for chunk in model.call_stream(messages, **kwargs):
                        full_response += chunk
                    return full_response
                # Add it to the class prototype dynamically if needed
                # This is a bit hacky, better if BaseAgent provided it or if VLLMModel had it
                if not hasattr(VLLMModel, 'call_stream_and_aggregate'):
                     VLLMModel.call_stream_and_aggregate = _stream_and_aggregate_helper
                # --- End helper method addition ---

                vllm_model_instance = VLLMModel(
                    model_name=MODEL_NAME,
                    api_url=API_URL,
                    api_key=API_KEY,
                    default_max_tokens=DEFAULT_MAX_TOKENS,
                    default_temperature=DEFAULT_TEMPERATURE
                )
                logger.info("VLLM Model instance created.")
            except Exception as e:
                logger.error(f"Fatal Error: Failed to initialize VLLM Model: {e}", exc_info=True)
                raise RuntimeError(f"Could not initialize VLLM Model: {e}")
        return vllm_model_instance
# --- End Model Setup ---


# --- Helper Functions (Keep existing strip_think_tags, find_logical_name_for_handle) ---
def strip_think_tags(text: str) -> str:
     # Keep existing logic...
    if not isinstance(text, str):
        return text
    think_end_tag = "</think>"
    tag_pos = text.find(think_end_tag)
    if tag_pos != -1:
        logger.debug("Found </think> tag, stripping preceding content.")
        content_after = text[tag_pos + len(think_end_tag):].strip()
        return content_after
    else:
        # logger.debug("No </think> tag found, using full response.") # Reduce noise
        return text.strip()

def find_logical_name_for_handle(definition: Dict, handle_id: str, io_type: str) -> Optional[str]:
     # Keep existing logic...
    if not definition or io_type not in definition:
        return None
    io_map = definition[io_type]
    for logical_name, details in io_map.items():
        if isinstance(details, dict) and details.get('handle_id') == handle_id:
            return logical_name
    if handle_id in io_map:
        # logger.debug(f"Falling back to using handle_id '{handle_id}' as logical name for {io_type}.")
        return handle_id
    return None
# --- End Helper Functions ---


# --- Dynamic Flow Execution Logic ---
async def run_flow(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """
    Executes the flow topologically based on nodes and edges.
    Passes data between nodes according to edge connections and handle mapping.
    Strips <think> tags from string outputs before logging or passing downstream.
    Injects run_id for specific agents.
    Appends preview link to the final log if generated.
    """
    # --- NEW: Generate Run ID ---
    run_id = f"run_{int(time.time())}_{os.urandom(4).hex()}"
    logger.info(f"--- Starting Dynamic Flow Execution ({run_id}) ---")
    output_log = [f"--- Flow Execution Start ({run_id}) ---"]
    start_time = time.time()
    final_preview_link = None # Store the link if generated

    # (Keep graph building and dependency logic...)
    if not nodes:
        output_log.append("No nodes found in the flow.")
        output_log.append(f"--- Flow Execution End ({run_id}) ---")
        return "\n".join(output_log)

    adj: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
    in_degree: Dict[str, int] = defaultdict(int)
    node_map: Dict[str, Dict] = {node['id']: node for node in nodes}
    all_node_ids: Set[str] = set(node_map.keys())
    connected_logical_inputs: Dict[str, Dict[str, bool]] = defaultdict(dict)

    for edge in edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        source_handle = edge.get('sourceHandle')
        target_handle = edge.get('targetHandle')
        if source_id in all_node_ids and target_id in all_node_ids and source_handle and target_handle:
            adj[source_id].append((target_id, source_handle, target_handle))
            in_degree[target_id] += 1
            target_definition = get_definition(node_map.get(target_id, {}).get('type'))
            logical_input_name = find_logical_name_for_handle(target_definition, target_handle, 'inputs')
            if logical_input_name:
                connected_logical_inputs[target_id][logical_input_name] = True
                # logger.debug(f"[{run_id}] Edge maps: {source_id}[{source_handle}] -> {target_id}[{target_handle}] (logical input: '{logical_input_name}')")
            else:
                logger.warning(f"[{run_id}] Edge target handle '{target_handle}' on node {target_id} does not map to a defined logical input.")
        else:
            logger.warning(f"[{run_id}] Skipping invalid edge: {edge}")


    # 2. Initialize Execution State (Keep existing)
    queue = deque([node_id for node_id in all_node_ids if in_degree[node_id] == 0])
    execution_results: Dict[str, Dict[str, Any]] = {} # node_id -> {logical_output_name: stripped_value}
    node_input_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
    executed_nodes: Set[str] = set()
    agent_instances: Dict[str, Any] = {}

    # Get model instance once (Keep existing)
    try:
        model = await get_model()
    except RuntimeError as e:
        output_log.append(f"\n## FATAL ERROR: Could not initialize model: {e} ##")
        output_log.append(f"--- Flow Execution End ({run_id}) ---")
        return "\n".join(output_log)

    # Instantiate agents/systems (Keep existing)
    for node_id, node in node_map.items():
        node_type = node.get('type')
        definition = get_definition(node_type)
        if definition and definition.get('constructor'):
            try:
                agent_instances[node_id] = definition['constructor'](model)
                logger.info(f"[{run_id}] Instantiated agent/system for node {node_id} ({node_type})")
            except Exception as e:
                logger.error(f"[{run_id}] Failed to instantiate node {node_id} ({node_type}): {e}", exc_info=True)
                output_log.append(f"\n## ERROR: Failed to instantiate node {node_id} ({node_type}): {e} ##")


    # 3. Execute Nodes Topologically
    exec_count = 0
    while queue:
        # (Keep cycle detection...)
        exec_count += 1
        if exec_count > len(all_node_ids) * 2:
             logger.error(f"[{run_id}] Potential cycle detected or excessive execution. Stopping.")
             output_log.append("\n## ERROR: Potential cycle detected or flow stuck. Execution halted. ##")
             break

        node_id = queue.popleft()

        # (Keep checks for node existence, instantiation, definition...)
        if node_id not in node_map: continue
        if node_id not in agent_instances:
            node_type_for_log = node_map.get(node_id, {}).get('type', 'Unknown Type')
            logger.warning(f"[{run_id}] Node {node_id} ({node_type_for_log}) was not instantiated successfully. Skipping execution.")
            output_log.append(f"\n--- Node: {node_id} ({node_type_for_log}) ---")
            output_log.append(f"Status: SKIPPED (Instantiation Failed)")
            continue

        node = node_map[node_id]
        node_type = node.get('type')
        definition = get_definition(node_type)
        agent_instance = agent_instances[node_id]

        if not definition or not definition.get('execute_function'):
             logger.warning(f"[{run_id}] No definition or execute_function for node {node_id} ({node_type}). Skipping.")
             output_log.append(f"\n--- Node: {node_id} ({node_type}) ---")
             output_log.append(f"Status: SKIPPED (No execute function defined)")
             continue

        # Gather input data (Keep existing logic)
        current_node_inputs = node.get('data', {}).copy()
        defined_input_names = set(definition.get('inputs', {}).keys())
        # --- SPECIAL CASE: Ensure 'run_id' from definition is included even if not in node data ---
        if 'run_id' in defined_input_names:
             defined_input_names.add('run_id')
        # --- END SPECIAL CASE ---
        current_node_inputs = {k: v for k, v in current_node_inputs.items() if k in defined_input_names}
        current_node_inputs.update(node_input_data[node_id])

        # --- NEW: Inject run_id if the agent expects it ---
        if 'run_id' in definition.get('inputs', {}):
            current_node_inputs['run_id'] = run_id
            logger.debug(f"[{run_id}] Injected run_id into inputs for node {node_id}")
        # --- END NEW ---

        # Check for missing required inputs (Keep existing logic)
        missing_required = False
        for logical_name, details in definition.get('inputs', {}).items():
            # Skip run_id check here, as it's injected
            if logical_name == 'run_id': continue
            is_required = details.get('required', False)
            # Check if required and EITHER visually connected but data missing OR not connected at all
            is_connected = connected_logical_inputs.get(node_id, {}).get(logical_name, False)
            has_data = logical_name in current_node_inputs

            if is_required and ((is_connected and not has_data) or (not is_connected and not has_data)):
                 logger.error(f"[{run_id}] Node {node_id}: Required input '{logical_name}' is missing.")
                 output_log.append(f"\n--- Node: {node_id} ({node_type}) ---")
                 output_log.append(f"Status: FAILED")
                 output_log.append(f"Error: Missing required input data for '{logical_name}'.")
                 missing_required = True
                 break

        if missing_required:
             continue

        logger.info(f"[{run_id}] Executing Node: {node_id} ({node_type}) ...") # Simplified log
        output_log.append(f"\n--- Node: {node_id} ({node_type}) ---")

        try:
            # Execute the node's logic (Keep existing)
            raw_node_outputs = await definition['execute_function'](agent_instance, current_node_inputs)

            # (Keep output processing and validation...)
            if not isinstance(raw_node_outputs, dict):
                 logger.warning(f"[{run_id}] Node {node_id} execution function did not return a dictionary. Result: {raw_node_outputs}")
                 output_keys = list(definition.get('outputs', {}).keys())
                 if len(output_keys) == 1:
                      raw_node_outputs = {output_keys[0]: raw_node_outputs}
                 else:
                      raw_node_outputs = {"output": str(raw_node_outputs)}

            # Strip <think> tags from string outputs (Keep existing)
            processed_node_outputs = {}
            for logical_out_name, out_value in raw_node_outputs.items():
                if isinstance(out_value, str):
                    stripped_value = strip_think_tags(out_value)
                    # if stripped_value != out_value: logger.info(f"[{run_id}] Node {node_id}: Stripped <think> tags from output '{logical_out_name}'.") # Reduce noise
                    processed_node_outputs[logical_out_name] = stripped_value
                else:
                    processed_node_outputs[logical_out_name] = out_value

            execution_results[node_id] = processed_node_outputs
            executed_nodes.add(node_id)

            # Log success and *stripped* output (Keep existing)
            output_log.append(f"Status: Success")
            for logical_out_name, stripped_value in processed_node_outputs.items():
                 # --- NEW: Capture Preview Link ---
                 if node_type == 'fileGeneratorAgent' and logical_out_name == 'preview_link' and stripped_value:
                     final_preview_link = stripped_value
                     logger.info(f"[{run_id}] Captured preview link: {final_preview_link}")
                     output_log.append(f"Output '{logical_out_name}': Preview link generated (see end of log).") # Don't log the link itself here
                 elif logical_out_name == 'generation_summary': # Just log the summary directly
                     output_log.append(f"Output '{logical_out_name}':\n{str(stripped_value)}")
                 elif logical_out_name != 'preview_link': # Avoid logging the link value twice
                     # Truncate long outputs for readability in main log
                     log_value = str(stripped_value)
                     if len(log_value) > 500:
                         log_value = log_value[:500] + "... (truncated)"
                     output_log.append(f"Output '{logical_out_name}':\n{log_value}")

            logger.info(f"[{run_id}] Node {node_id} execution successful.")

            # Process downstream nodes (Keep existing logic for passing data and checking readiness)
            for target_id, source_handle, target_handle in adj[node_id]:
                 target_node = node_map.get(target_id)
                 target_definition = get_definition(target_node.get('type')) if target_node else None

                 if target_node and target_definition:
                    logical_output_name = find_logical_name_for_handle(definition, source_handle, 'outputs')
                    logical_input_name = find_logical_name_for_handle(target_definition, target_handle, 'inputs')

                    if logical_output_name and logical_input_name:
                        output_value_to_pass = processed_node_outputs.get(logical_output_name)
                        if output_value_to_pass is not None:
                            node_input_data[target_id][logical_input_name] = output_value_to_pass
                            # logger.debug(f"[{run_id}] Passing '{logical_output_name}' from {node_id} to '{logical_input_name}' of {target_id}")
                        else:
                             logger.warning(f"[{run_id}] Logical output '{logical_output_name}' not found in processed results of {node_id}. Cannot pass.")
                    else:
                        logger.warning(f"[{run_id}] Could not map handles for edge {node_id}[{source_handle}] -> {target_id}[{target_handle}].")

                    in_degree[target_id] -= 1
                    if in_degree[target_id] == 0:
                        # Keep readiness check logic...
                        is_ready = True
                        target_reqs = target_definition.get('inputs', {})
                        for req_logical_name, details in target_reqs.items():
                             if req_logical_name == 'run_id': continue # Skip run_id check
                             is_req = details.get('required', False)
                             was_connected = connected_logical_inputs.get(target_id, {}).get(req_logical_name, False)
                             has_data = req_logical_name in node_input_data[target_id]
                             if is_req and ((was_connected and not has_data) or (not was_connected and not has_data)):
                                  is_ready = False
                                  # logger.debug(f"[{run_id}] Node {target_id} still waiting for required input '{req_logical_name}'.")
                                  break
                        if is_ready and target_id not in executed_nodes and target_id not in queue:
                           logger.info(f"[{run_id}] Node {target_id} is ready. Adding to queue.")
                           queue.append(target_id)
                        # elif not is_ready and target_id not in executed_nodes:
                        #      logger.debug(f"[{run_id}] Node {target_id} has in_degree 0 but still waiting.")

        except Exception as e:
             # (Keep existing exception handling)
            logger.error(f"[{run_id}] Error during execution or downstream processing for node {node_id} ({node_type}): {e}", exc_info=True)
            output_log.append(f"Status: FAILED")
            output_log.append(f"Error:\n{e}")

    # 4. Compile Final Output Log
    output_log.append(f"\n--- Execution Summary ({run_id}) ---")
    # (Keep existing summary logic)
    executed_count = len(executed_nodes)
    total_nodes = len(all_node_ids)
    if executed_count == total_nodes:
         output_log.append("All nodes executed successfully.")
    else:
         output_log.append(f"Executed {executed_count}/{total_nodes} nodes.")
         failed_or_skipped = all_node_ids - executed_nodes
         if failed_or_skipped:
             output_log.append(f"Failed/Skipped/Waiting nodes: {', '.join(failed_or_skipped)}")

    end_time = time.time()
    output_log.append(f"Total execution time: {end_time - start_time:.2f} seconds")

    # --- NEW: Append Preview Link if Available ---
    if final_preview_link:
        output_log.append("\n--- Preview Link ---")
        # Use a clear marker for the frontend to detect
        output_log.append(f"PREVIEW_LINK::{final_preview_link}")
        # Also add a user-friendly message
        output_log.append(f"(Link to preview generated content: {final_preview_link} )")
    # --- END NEW ---

    output_log.append(f"\n--- Flow Execution End ({run_id}) ---")
    logger.info(f"--- Dynamic Flow Execution Finished ({run_id}) ---")

    return "\n".join(output_log)
