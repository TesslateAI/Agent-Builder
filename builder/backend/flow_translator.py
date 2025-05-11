# builder/backend/flow_translator.py
import inspect
import logging
from typing import List, Dict, Any, Tuple
from collections import deque

from tframex import Flow
from tframex import patterns as tframex_patterns_module # Module itself
from tframex.patterns import BasePattern # Base class for type checking
from tframex_config import get_tframex_app_instance

logger = logging.getLogger("FlowTranslator")

def translate_visual_to_tframex_flow(
    flow_id: str,
    visual_nodes: List[Dict[str, Any]],
    visual_edges: List[Dict[str, Any]]
) -> Tuple[Flow | None, List[str]]:
    """
    Translates a visual flow (ReactFlow nodes and edges) into an executable tframex.Flow.
    Handles agent steps and pattern steps with their configurations.
    Returns the constructed Flow object and a list of log messages.
    """
    app = get_tframex_app_instance()
    translation_log = [f"--- Flow Translation Start (Visual Flow ID: {flow_id}) ---"]
    
    if not visual_nodes:
        translation_log.append("Error: No visual nodes provided for flow translation.")
        return None, translation_log

    node_map: Dict[str, Dict] = {node['id']: node for node in visual_nodes}
    adj: Dict[str, List[str]] = {node_id: [] for node_id in node_map}
    in_degree: Dict[str, int] = {node_id: 0 for node_id in node_map}
    
    for edge in visual_edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        
        if source_id in node_map and target_id in node_map:
            # Consider edges primarily between agent/pattern nodes for main flow sequence
            source_node_data = node_map[source_id].get('data', {})
            target_node_data = node_map[target_id].get('data', {})
            
            is_source_flow_element = source_node_data.get('component_category') in ['agent', 'pattern']
            is_target_flow_element = target_node_data.get('component_category') in ['agent', 'pattern']

            # This edge defines execution order if both source and target are flow elements
            if is_source_flow_element and is_target_flow_element:
                # And it's not a configuration edge (like tool to agent)
                # Simple check: if sourceHandle and targetHandle are typical flow handles
                # Frontend should ideally mark flow edges vs config edges.
                # For now, assume if source is not a 'tool', it's a flow edge to another agent/pattern.
                if source_node_data.get('component_category') != 'tool':
                    adj[source_id].append(target_id)
                    in_degree[target_id] += 1
                    translation_log.append(f"  Graph edge (flow): {source_id} -> {target_id}")
            elif source_node_data.get('component_category') == 'tool' and is_target_flow_element:
                translation_log.append(f"  Config edge (visual only): Tool {source_id} to Agent/Pattern {target_id}")
            # Other edge types (e.g., agent output to pattern config input) are not for graph sorting,
            # but their data is used during pattern instantiation.

    # Topological sort for execution order of main flow elements
    queue = deque()
    for node_id in node_map:
        node_data = node_map[node_id].get('data', {})
        if node_data.get('component_category') in ['agent', 'pattern'] and in_degree[node_id] == 0:
            queue.append(node_id)
            
    sorted_node_ids_for_flow = []
    visited_for_sort = set()

    while queue:
        u_id = queue.popleft()
        if u_id in visited_for_sort: continue
        visited_for_sort.add(u_id)
        sorted_node_ids_for_flow.append(u_id)
        
        for v_id in adj[u_id]: # adj only contains flow element connections
            in_degree[v_id] -= 1
            if in_degree[v_id] == 0: # No need to check category again, adj ensures it's flow element
                queue.append(v_id)

    num_flow_elements = sum(1 for nid in node_map if node_map[nid].get('data',{}).get('component_category') in ['agent', 'pattern'])
    if len(sorted_node_ids_for_flow) != num_flow_elements:
        translation_log.append(
            f"Warning: Flow graph might have issues. Sorted {len(sorted_node_ids_for_flow)} of {num_flow_elements} agent/pattern nodes. "
            f"Untraversed flow nodes: {set(node_map.keys()) - visited_for_sort - set(nid for nid in node_map if node_map[nid].get('data',{}).get('component_category') == 'tool')}"
        )
        # For robustness, we proceed with sorted nodes but log clearly.

    translation_log.append(f"  Topological Sort for TFrameX Flow Steps: {sorted_node_ids_for_flow}")

    constructed_flow = Flow(flow_name=f"studio_visual_flow_{flow_id}")

    for node_id_in_flow_order in sorted_node_ids_for_flow:
        node_config = node_map.get(node_id_in_flow_order)
        if not node_config:
            translation_log.append(f"  Warning: Node ID '{node_id_in_flow_order}' from sort not found in node_map. Skipping.")
            continue

        # 'type' from visual node IS the TFrameX agent name or Pattern class name
        tframex_component_id = node_config.get('type') 
        node_data_from_frontend = node_config.get('data', {}) # Config from the visual node's UI
        component_category = node_data_from_frontend.get('component_category')

        if not tframex_component_id:
            translation_log.append(f"  Warning: Node '{node_id_in_flow_order}' (Data: {node_data_from_frontend.get('label', 'N/A')}) has no 'type' (TFrameX ID). Skipping.")
            continue

        translation_log.append(f"\nProcessing Visual Node: '{node_data_from_frontend.get('label', node_id_in_flow_order)}' (Type: {tframex_component_id}, Category: {component_category})")

        if component_category == 'agent':
            if tframex_component_id in app._agents:
                # Agent step. The 'type' is the TFrameX agent's registered name.
                # Frontend 'data.selected_tools' is now used by the TFrameXRuntimeContext
                # during agent instantiation if that logic is added to tframex or our wrapper.
                # For now, TFrameX will use tools from @app.agent decorator.
                # Template vars are passed globally to run_flow.
                constructed_flow.add_step(tframex_component_id)
                translation_log.append(f"  Added TFrameX Agent Step: '{tframex_component_id}'")
            else:
                translation_log.append(f"  Error: Agent '{tframex_component_id}' not registered in TFrameX. Skipping step.")
                logger.error(f"Flow Translation: Agent '{tframex_component_id}' for node '{node_id_in_flow_order}' not found in TFrameX app registry.")

        elif component_category == 'pattern':
            if not hasattr(tframex_patterns_module, tframex_component_id):
                translation_log.append(f"  Error: Pattern class '{tframex_component_id}' not found in tframex.patterns. Skipping.")
                logger.error(f"Flow Translation: Pattern class '{tframex_component_id}' for node '{node_id_in_flow_order}' not found.")
                continue
                
            PatternClass = getattr(tframex_patterns_module, tframex_component_id)
            if not (inspect.isclass(PatternClass) and issubclass(PatternClass, BasePattern)):
                translation_log.append(f"  Error: '{tframex_component_id}' is not a valid TFrameX Pattern class. Skipping.")
                continue

            pattern_init_params = {}
            sig = inspect.signature(PatternClass.__init__)
            missing_required_params = []

            # Populate pattern_init_params from node_data_from_frontend
            # The keys in node_data_from_frontend should match the constructor param names of the TFrameX Pattern.
            for param_name_in_sig, param_obj_in_sig in sig.parameters.items():
                if param_name_in_sig in ['self', 'pattern_name', 'args', 'kwargs']:
                    continue
                
                # Frontend must send data keys matching constructor params for patterns
                # e.g., for SequentialPattern, frontend data might have a "steps" key
                # (previously called "steps_config")
                if param_name_in_sig in node_data_from_frontend:
                    value = node_data_from_frontend[param_name_in_sig]
                    
                    # Type coercion or validation might be needed here based on param_obj_in_sig.annotation
                    # Example: Ensure lists of agent names are actually lists of valid strings
                    if param_name_in_sig in ["steps", "tasks", "participant_agent_names"] and isinstance(value, list):
                        valid_agents_for_pattern = []
                        for item in value:
                            if isinstance(item, str) and item in app._agents:
                                valid_agents_for_pattern.append(item)
                            else:
                                translation_log.append(f"  Warning: Invalid/unregistered agent name '{item}' found in '{param_name_in_sig}' for pattern '{tframex_component_id}'. It will be excluded.")
                        pattern_init_params[param_name_in_sig] = valid_agents_for_pattern
                    elif param_name_in_sig in ["router_agent_name", "moderator_agent_name", "default_route"] and isinstance(value, str):
                        if value and value not in app._agents: # Also check if 'value' is a pattern name for default_route
                             if not (param_name_in_sig == "default_route" and hasattr(tframex_patterns_module, value)):
                                translation_log.append(f"  Warning: Agent/Pattern name '{value}' for '{param_name_in_sig}' in Pattern '{tframex_component_id}' is not registered. Pattern might fail.")
                        pattern_init_params[param_name_in_sig] = value if value else None # Allow empty string to be None if appropriate
                    elif param_name_in_sig == "routes" and isinstance(value, dict):
                        valid_routes = {}
                        for k, route_target_name in value.items():
                            if isinstance(route_target_name, str) and route_target_name and \
                               (route_target_name in app._agents or hasattr(tframex_patterns_module, route_target_name)):
                                valid_routes[k] = route_target_name
                            else:
                                translation_log.append(f"  Warning: Invalid route target '{route_target_name}' for key '{k}' in Pattern '{tframex_component_id}'.")
                        pattern_init_params[param_name_in_sig] = valid_routes
                    elif param_name_in_sig == "discussion_rounds" and value is not None:
                        try:
                            pattern_init_params[param_name_in_sig] = int(value)
                        except ValueError:
                            translation_log.append(f"  Warning: Invalid integer value '{value}' for '{param_name_in_sig}' in Pattern '{tframex_component_id}'. Using default or pattern might fail.")
                            # Let pattern's own validation handle it or use a default.
                    else:
                        pattern_init_params[param_name_in_sig] = value
                elif param_obj_in_sig.default == inspect.Parameter.empty: # Required param, not provided
                    missing_required_params.append(param_name_in_sig)
            
            if missing_required_params:
                translation_log.append(f"  Error: Pattern '{tframex_component_id}' (Node: {node_data_from_frontend.get('label', node_id_in_flow_order)}) is missing required constructor parameters: {missing_required_params}. Skipping pattern.")
                continue

            try:
                # pattern_name for TFrameX Pattern constructor is mandatory
                pattern_display_name = node_data_from_frontend.get('label', node_id_in_flow_order).replace(" ", "_")
                instance_pattern_name = f"p_{pattern_display_name}_{node_id_in_flow_order[:4]}"

                pattern_instance = PatternClass(pattern_name=instance_pattern_name, **pattern_init_params)
                constructed_flow.add_step(pattern_instance)
                translation_log.append(f"  Added TFrameX Pattern Step: '{tframex_component_id}' (Instance: {pattern_instance.pattern_name}) with params: {pattern_init_params}")
            except Exception as e:
                translation_log.append(f"  Error instantiating Pattern '{tframex_component_id}' (Node: {node_data_from_frontend.get('label', node_id_in_flow_order)}) with params {pattern_init_params}: {e}")
                logger.error(f"Flow Translation: Error instantiating Pattern '{tframex_component_id}': {e}", exc_info=True)
        
        elif component_category == 'tool':
            translation_log.append(f"  Info: Visual Tool Node '{tframex_component_id}' (Node: {node_data_from_frontend.get('label', node_id_in_flow_order)}) is not directly added as a TFrameX flow step. It configures Agents.")
        else:
            translation_log.append(f"  Warning: Visual node '{node_data_from_frontend.get('label', node_id_in_flow_order)}' (Type: {tframex_component_id}) has unknown category '{component_category}'. Skipping.")

    if not constructed_flow.steps:
        translation_log.append("\nError: No valid executable steps were translated into the TFrameX Flow.")
        # Return None for the flow object if no steps, but still return logs
        return None, translation_log
        
    translation_log.append("--- Flow Translation End ---")
    return constructed_flow, translation_log