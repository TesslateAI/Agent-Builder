# backend/flow_translator.py
import inspect
import logging
from typing import List, Dict, Any, Tuple
from collections import deque
import copy
import hashlib

from tframex import Flow, TFrameXApp # Import TFrameXApp for type hinting
from tframex import patterns as tframex_patterns_module
from tframex.patterns import BasePattern
# from tframex_config import get_tframex_app_instance # Not used directly, app instances are passed

logger = logging.getLogger("FlowTranslator")

def _generate_unique_suffix_for_instance(config_dict, canvas_node_id):
    """Generates a short hash suffix based on a dictionary and canvas ID to make names unique."""
    hasher = hashlib.md5()
    # Include canvas_node_id in the hash to differentiate nodes even if they have identical override configs
    # (though less likely for agents, more for ensuring uniqueness)
    combined_repr = str(sorted(config_dict.items())) + f"_nodeid_{canvas_node_id}"
    encoded = combined_repr.encode('utf-8')
    hasher.update(encoded)
    return hasher.hexdigest()[:8] # Slightly longer for more uniqueness

def translate_visual_to_tframex_flow(
    flow_id: str,
    visual_nodes: List[Dict[str, Any]],
    visual_edges: List[Dict[str, Any]],
    global_app_instance: TFrameXApp,       # Source of base definitions
    current_run_app_instance: TFrameXApp   # Target for this run's specific agent configs & flow
) -> Tuple[Flow | None, List[str], Dict[str, str]]:
    """
    Translates a visual flow into an executable tframex.Flow using the current_run_app_instance.
    Agent overrides result in temporary agent registrations on current_run_app_instance.
    Returns the Flow, log messages, and a map of canvas node IDs to effective TFrameX names.
    """
    translation_log = [f"--- Flow Translation Start (Visual Flow ID: {flow_id}) ---"]
    canvas_node_to_effective_name_map: Dict[str, str] = {} # Maps canvas node ID to its TFrameX name on current_run_app

    if not visual_nodes:
        translation_log.append("Error: No visual nodes provided for flow translation.")
        return None, translation_log, canvas_node_to_effective_name_map

    # --- Pre-pass: Register all agents (original or overridden) on current_run_app_instance ---
    translation_log.append("\n--- Pre-processing Agent Nodes for Current Run App ---")
    for node_config in visual_nodes:
        if node_config.get('data', {}).get('component_category') == 'agent':
            canvas_node_id = node_config['id']
            original_tframex_id = node_config['type'] # This is the base agent ID from global app
            node_data = node_config.get('data', {})

            if original_tframex_id not in global_app_instance._agents:
                msg = f"  Base Agent Definition '{original_tframex_id}' for canvas node '{canvas_node_id}' not found in global app. Skipping."
                translation_log.append(msg)
                logger.warning(msg)
                continue

            base_agent_reg_info = global_app_instance._agents[original_tframex_id]
            # Start with a deepcopy of the base agent's registered configuration
            effective_config = copy.deepcopy(base_agent_reg_info.get("config", {}))
            
            # Define base values from the agent's original definition for comparison
            # These keys match what component_manager provides to the frontend
            base_decorator_config = base_agent_reg_info.get("config", {})
            base_values_for_comparison = {
                "system_prompt": base_agent_reg_info.get("config", {}).get("system_prompt_template", ""),
                "tool_names": sorted(base_agent_reg_info.get("config", {}).get("tool_names", [])),
                "strip_think_tags": base_agent_reg_info.get("config", {}).get("strip_think_tags", False)
            }

            config_values_for_hashing = {} # Store actual overridden values that differ from base

            # Apply system_prompt_override
            node_system_prompt_override = node_data.get('system_prompt_override')
            if node_system_prompt_override and node_system_prompt_override.strip():
                # Store the override under 'system_prompt_template' for the agent's runtime config.
                # LLMAgent likely uses 'system_prompt_template' internally for rendering.
                effective_config['system_prompt_template'] = node_system_prompt_override
                if node_system_prompt_override != base_values_for_comparison["system_prompt"]:
                    config_values_for_hashing['system_prompt'] = node_system_prompt_override
            else: # No override or empty override, ensure effective_config has the base prompt.
                effective_config['system_prompt_template'] = base_values_for_comparison["system_prompt"]
            
            # Remove the original 'system_prompt' key if it was just a boolean indicator from the decorator
            if 'system_prompt' in effective_config and isinstance(effective_config['system_prompt'], bool):
                del effective_config['system_prompt']

            # Apply selected_tools override
            node_selected_tools = node_data.get('selected_tools')
            # Check for None explicitly as an empty list [] is a valid override
            if node_selected_tools is not None and isinstance(node_selected_tools, list):
                valid_tools = sorted([t for t in node_selected_tools if t in current_run_app_instance._tools])
                effective_config['tool_names'] = valid_tools # Set for runtime
                if valid_tools != base_values_for_comparison["tool_names"]: # Compare sorted lists
                    config_values_for_hashing['tool_names'] = valid_tools
            else: # No 'selected_tools' in node_data, agent uses its default tools.
                effective_config['tool_names'] = base_values_for_comparison["tool_names"]

            # Apply strip_think_tags_override
            if 'strip_think_tags_override' in node_data:
                node_strip_tags_override = node_data['strip_think_tags_override']
                effective_config['strip_think_tags'] = node_strip_tags_override # Set for runtime
                if node_strip_tags_override != base_values_for_comparison["strip_think_tags"]:
                    config_values_for_hashing['strip_think_tags'] = node_strip_tags_override
            else: # No override for strip_think_tags
                effective_config['strip_think_tags'] = base_values_for_comparison["strip_think_tags"]

            effective_agent_name_for_run = original_tframex_id
            if config_values_for_hashing: # If any actual values were different and recorded for hashing
                unique_suffix = _generate_unique_suffix_for_instance(config_values_for_hashing, canvas_node_id)
                effective_agent_name_for_run = f"{original_tframex_id}_run_{unique_suffix}"
                translation_log.append(f"  Canvas Node '{canvas_node_id}' (Base: {original_tframex_id}): Overrides for {list(config_values_for_hashing.keys())}. Effective name: '{effective_agent_name_for_run}'")
            else:
                translation_log.append(f"  Canvas Node '{canvas_node_id}' (Base: {original_tframex_id}): Config matches base or no differing overrides. Effective name: '{original_tframex_id}'")


            # Register this configuration on the current_run_app_instance
            if effective_agent_name_for_run not in current_run_app_instance._agents:
                current_run_app_instance._agents[effective_agent_name_for_run] = {
                    "func_ref": base_agent_reg_info.get("func_ref"), # Placeholder function
                    "config": effective_config,
                    "agent_class_ref": base_agent_reg_info.get("agent_class_ref")
                }
                translation_log.append(f"    Registered '{effective_agent_name_for_run}' on current run app instance.")
            elif effective_agent_name_for_run != original_tframex_id : # It was an overridden agent already registered
                translation_log.append(f"    Re-using already registered overridden agent '{effective_agent_name_for_run}' on current run app instance.")

            canvas_node_to_effective_name_map[canvas_node_id] = effective_agent_name_for_run
    translation_log.append("--- End Agent Pre-processing ---")

    # --- Standard Topological Sort for Flow Construction ---
    node_map: Dict[str, Dict] = {node['id']: node for node in visual_nodes}
    adj: Dict[str, List[str]] = {node_id: [] for node_id in node_map}
    in_degree: Dict[str, int] = {node_id: 0 for node_id in node_map}

    for edge in visual_edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        if source_id in node_map and target_id in node_map:
            source_node_data = node_map[source_id].get('data', {})
            target_node_data = node_map[target_id].get('data', {})
            is_source_flow_element = source_node_data.get('component_category') in ['agent', 'pattern']
            is_target_flow_element = target_node_data.get('component_category') in ['agent', 'pattern']
            if is_source_flow_element and is_target_flow_element and source_node_data.get('component_category') != 'tool':
                adj[source_id].append(target_id)
                in_degree[target_id] += 1

    queue = deque()
    for node_id_in_map in node_map: # Iterate all nodes present in the map
        node_data = node_map[node_id_in_map].get('data', {})
        # Only consider agent/pattern nodes for starting points of topo sort
        if node_data.get('component_category') in ['agent', 'pattern'] and in_degree[node_id_in_map] == 0:
            queue.append(node_id_in_map)

    sorted_canvas_node_ids_for_flow = []
    visited_for_sort = set()
    while queue:
        u_id = queue.popleft()
        if u_id in visited_for_sort: continue
        visited_for_sort.add(u_id)
        sorted_canvas_node_ids_for_flow.append(u_id)
        for v_id in adj[u_id]:
            in_degree[v_id] -= 1
            if in_degree[v_id] == 0:
                queue.append(v_id)

    num_flow_elements_on_canvas = sum(1 for nid in node_map if node_map[nid].get('data',{}).get('component_category') in ['agent', 'pattern'])
    if len(sorted_canvas_node_ids_for_flow) != num_flow_elements_on_canvas:
        translation_log.append(
            f"Warning: Flow graph might have issues. Sorted {len(sorted_canvas_node_ids_for_flow)} of {num_flow_elements_on_canvas} agent/pattern canvas nodes. "
            f"Untraversed flow nodes: {set(n['id'] for n in visual_nodes if n.get('data',{}).get('component_category') in ['agent','pattern']) - visited_for_sort}"
        )
    translation_log.append(f"  Topological Sort for Flow Steps (Canvas Node IDs): {sorted_canvas_node_ids_for_flow}")

    # --- Construct Flow using current_run_app_instance ---
    constructed_flow = Flow(flow_name=f"studio_visual_flow_{flow_id}")
    for canvas_node_id_in_flow_order in sorted_canvas_node_ids_for_flow:
        node_config = node_map.get(canvas_node_id_in_flow_order)
        if not node_config: continue # Should not happen if sort is correct

        node_data_from_frontend = node_config.get('data', {})
        component_category = node_data_from_frontend.get('component_category')
        # original_tframex_component_id is the 'type' from ReactFlow, e.g. "MyBaseAgent" or "SequentialPattern"
        original_tframex_component_id = node_config.get('type')

        translation_log.append(f"\nProcessing Sorted Canvas Node: '{node_data_from_frontend.get('label', canvas_node_id_in_flow_order)}' (Base Type: {original_tframex_component_id}, Category: {component_category})")

        if component_category == 'agent':
            effective_agent_name = canvas_node_to_effective_name_map.get(canvas_node_id_in_flow_order)
            if effective_agent_name and effective_agent_name in current_run_app_instance._agents:
                constructed_flow.add_step(effective_agent_name)
                translation_log.append(f"  Added Agent Step to Flow: '{effective_agent_name}'")
            else:
                msg = f"  Error: Effective agent name for canvas node '{canvas_node_id_in_flow_order}' ('{effective_agent_name}') not found or not registered on current run app. Skipping step."
                translation_log.append(msg)
                logger.error(msg)

        elif component_category == 'pattern':
            PatternClass = getattr(tframex_patterns_module, original_tframex_component_id, None)
            if not (PatternClass and inspect.isclass(PatternClass) and issubclass(PatternClass, BasePattern)):
                translation_log.append(f"  Error: Pattern class '{original_tframex_component_id}' not found or invalid. Skipping.")
                continue

            pattern_init_params = {}
            sig = inspect.signature(PatternClass.__init__)
            missing_required_params = []

            for param_name_in_sig, param_obj_in_sig in sig.parameters.items():
                if param_name_in_sig in ['self', 'pattern_name', 'args', 'kwargs']: continue

                if param_name_in_sig in node_data_from_frontend:
                    value = node_data_from_frontend[param_name_in_sig]

                    # Resolve agent/pattern names in parameters using the map
                    agent_ref_params = ["steps", "tasks", "participant_agent_names", "router_agent_name", "moderator_agent_name", "default_route"]
                    is_list_of_agents = param_name_in_sig in ["steps", "tasks", "participant_agent_names"]
                    is_single_agent_ref = param_name_in_sig in ["router_agent_name", "moderator_agent_name"]
                    is_route_target_ref = param_name_in_sig == "default_route" # Can be agent or pattern CLASS name

                    if is_list_of_agents and isinstance(value, list):
                        resolved_targets = []
                        for item_canvas_node_id_or_tframex_id in value:
                            # The 'item_canvas_node_id_or_tframex_id' is what TFrameXPatternNode stored in data.
                            # It should be the TFrameX component ID (original or from dropdown).
                            # If it was a connection, the frontend store.js onConnect should have stored the tframex_component_id
                            # of the source agent node.

                            # If this `item` is an ID of a canvas agent node that might have overrides, resolve it.
                            # Otherwise, assume it's a direct TFrameX name (e.g. another pattern's class name).
                            effective_name = canvas_node_to_effective_name_map.get(item_canvas_node_id_or_tframex_id, item_canvas_node_id_or_tframex_id)

                            # Validate against current_run_app (for agents) or tframex_patterns_module (for pattern classes)
                            if effective_name in current_run_app_instance._agents or \
                               hasattr(tframex_patterns_module, effective_name) or \
                               effective_name.startswith("p_"): # previously instantiated pattern
                                resolved_targets.append(effective_name)
                            else:
                                translation_log.append(f"  Warning: Invalid agent/pattern target '{effective_name}' (original ref: '{item_canvas_node_id_or_tframex_id}') in list '{param_name_in_sig}' for pattern '{original_tframex_component_id}'. Excluding.")
                        pattern_init_params[param_name_in_sig] = resolved_targets

                    elif (is_single_agent_ref or is_route_target_ref) and (value is None or isinstance(value, str)):
                        if value: # If not None or empty
                            # `value` here is expected to be a canvas node ID (if connected) or a TFrameX ID (if selected)
                            effective_name = canvas_node_to_effective_name_map.get(value, value)
                            is_valid_target = False
                            if effective_name in current_run_app_instance._agents: is_valid_target = True
                            elif is_route_target_ref and hasattr(tframex_patterns_module, effective_name): is_valid_target = True # Pattern class for default_route
                            elif is_route_target_ref and effective_name.startswith("p_"): is_valid_target = True # Instantiated pattern

                            if not is_valid_target:
                                translation_log.append(f"  Warning: Invalid target '{effective_name}' (original ref: '{value}') for '{param_name_in_sig}' in Pattern '{original_tframex_component_id}'. May fail.")
                            pattern_init_params[param_name_in_sig] = effective_name if effective_name else None
                        else:
                            pattern_init_params[param_name_in_sig] = None

                    elif param_name_in_sig == "routes" and isinstance(value, dict):
                        resolved_routes = {}
                        for k, target_canvas_node_id_or_tframex_id in value.items():
                            if isinstance(target_canvas_node_id_or_tframex_id, str) and target_canvas_node_id_or_tframex_id:
                                effective_name = canvas_node_to_effective_name_map.get(target_canvas_node_id_or_tframex_id, target_canvas_node_id_or_tframex_id)
                                if effective_name in current_run_app_instance._agents or \
                                   hasattr(tframex_patterns_module, effective_name) or \
                                   effective_name.startswith("p_"):
                                    resolved_routes[k] = effective_name
                                else:
                                    translation_log.append(f"  Warning: Invalid route target '{effective_name}' (original ref: {target_canvas_node_id_or_tframex_id}) for key '{k}' in Pattern '{original_tframex_component_id}'.")
                            else: # Handle null/empty target_name if needed, or skip
                                 translation_log.append(f"  Warning: Empty/invalid route target for key '{k}' in Pattern '{original_tframex_component_id}'.")
                        pattern_init_params[param_name_in_sig] = resolved_routes
                    elif param_name_in_sig == "discussion_rounds" and value is not None:
                        try: pattern_init_params[param_name_in_sig] = int(value)
                        except (ValueError, TypeError): translation_log.append(f"  Warning: Invalid integer for 'discussion_rounds'.")
                    else:
                        pattern_init_params[param_name_in_sig] = value
                elif param_obj_in_sig.default == inspect.Parameter.empty:
                    missing_required_params.append(param_name_in_sig)

            if missing_required_params:
                translation_log.append(f"  Error: Pattern '{original_tframex_component_id}' (Node: {canvas_node_id_in_flow_order}) missing params: {missing_required_params}. Skipping.")
                continue

            try:
                pattern_display_name = node_data_from_frontend.get('label', canvas_node_id_in_flow_order).replace(" ", "_").replace("-","_")
                instance_pattern_name = f"p_{pattern_display_name}_{canvas_node_id_in_flow_order[:4]}"
                pattern_instance = PatternClass(pattern_name=instance_pattern_name, **pattern_init_params)
                # The pattern instance will resolve agent/pattern names using the current_run_app_instance's context implicitly when run.
                constructed_flow.add_step(pattern_instance)
                translation_log.append(f"  Added Pattern Step to Flow: '{original_tframex_component_id}' (Instance: {instance_pattern_name}) with resolved params: {pattern_init_params}")
            except Exception as e:
                translation_log.append(f"  Error instantiating Pattern '{original_tframex_component_id}': {e}")
                logger.error(f"Error instantiating Pattern '{original_tframex_component_id}': {e}", exc_info=True)

        # Tool nodes and utility nodes are not added as direct flow steps
        elif component_category == 'tool':
            translation_log.append(f"  Info: Tool Node '{original_tframex_component_id}' (Canvas ID: {canvas_node_id_in_flow_order}) - not a direct flow step.")
        elif component_category == 'utility' and original_tframex_component_id == 'textInput':
             translation_log.append(f"  Info: Utility Node 'textInput' (Canvas ID: {canvas_node_id_in_flow_order}) - not a direct flow step.")
        elif component_category not in ['agent', 'pattern']: # Should be caught by topo sort if not agent/pattern
            translation_log.append(f"  Warning: Node '{canvas_node_id_in_flow_order}' (Type: {original_tframex_component_id}) has unknown category '{component_category}' or is not a flow element. Skipping.")


    if not constructed_flow.steps:
        translation_log.append("\nError: No valid executable steps were translated into the TFrameX Flow.")
        return None, translation_log, canvas_node_to_effective_name_map

    translation_log.append("--- Flow Translation End ---")
    return constructed_flow, translation_log, canvas_node_to_effective_name_map