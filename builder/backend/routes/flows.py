# routes/flows.py
import os
import asyncio
import json
import logging
import time
from flask import Blueprint, request, jsonify, g
from tframex import TFrameXApp, Message

from database import (
    create_project, get_project, list_projects,
    save_flow, get_flow, list_flows, delete_flow,
    create_flow_execution, update_flow_execution, get_flow_executions,
    create_audit_log
)
from component_manager import discover_tframex_components, register_code_dynamically
from flow_translator import translate_visual_to_tframex_flow
from middleware.auth import require_auth, get_current_user_id, get_current_organization_id
from auth.rbac import require_permission

logger = logging.getLogger("FlowsAPI")

flows_bp = Blueprint('flows', __name__, url_prefix='/api/tframex')

def get_global_tframex_app():
    """Get the global TFrameX app instance"""
    from tframex_config import get_tframex_app_instance
    return get_tframex_app_instance()

# --- Project Management ---

@flows_bp.route('/projects', methods=['GET', 'POST'])
@require_auth
def handle_projects():
    """List projects or create a new one"""
    user_id = get_current_user_id()
    organization_id = get_current_organization_id()
    
    if request.method == 'GET':
        # Apply organization filter for projects
        projects = list_projects()  # TODO: Filter by organization in database layer
        
        # Create audit log for project listing
        create_audit_log(
            user_id=user_id,
            organization_id=organization_id,
            action='list',
            resource_type='projects',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify(projects)
    
    elif request.method == 'POST':
        # Check permission to create projects
        from auth.rbac import RBACManager
        user_permissions = getattr(g, 'permissions', [])
        if not RBACManager.check_permission(user_permissions, 'projects.create'):
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Permission "projects.create" required'
            }), 403
        
        data = request.get_json()
        project_id = data.get('id', f"project_{int(time.time())}")
        name = data.get('name', 'Untitled Project')
        description = data.get('description', '')
        
        try:
            # Note: create_project needs to be updated to include organization_id and owner_id
            # For now, we'll use the existing function but this should be enhanced
            project = create_project(project_id, name, description)
            
            # Create audit log
            create_audit_log(
                user_id=user_id,
                organization_id=organization_id,
                action='create',
                resource_type='projects',
                resource_id=project_id,
                details={'name': name, 'description': description},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            return jsonify(project), 201
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return jsonify({"error": str(e)}), 500

# --- Flow Persistence ---

@flows_bp.route('/flows', methods=['GET', 'POST'])
def handle_flows():
    """List flows or save a new/updated flow"""
    if request.method == 'GET':
        project_id = request.args.get('project_id')
        flows = list_flows(project_id)
        return jsonify(flows)
    
    elif request.method == 'POST':
        data = request.get_json()
        flow_id = data.get('id', f"flow_{int(time.time())}")
        project_id = data.get('project_id', 'default_project')
        
        # Ensure project exists
        if not get_project(project_id):
            create_project(project_id, 'Default Project', 'Auto-created project')
        
        try:
            flow = save_flow(
                flow_id=flow_id,
                project_id=project_id,
                name=data.get('name', 'Untitled Flow'),
                nodes=data.get('nodes', []),
                edges=data.get('edges', []),
                description=data.get('description', ''),
                metadata=data.get('metadata', {})
            )
            return jsonify(flow), 201
        except Exception as e:
            logger.error(f"Error saving flow: {e}")
            return jsonify({"error": str(e)}), 500

@flows_bp.route('/flows/<flow_id>', methods=['GET', 'DELETE'])
def handle_flow(flow_id):
    """Get or delete a specific flow"""
    if request.method == 'GET':
        flow = get_flow(flow_id)
        if flow:
            return jsonify(flow)
        return jsonify({"error": "Flow not found"}), 404
    
    elif request.method == 'DELETE':
        if delete_flow(flow_id):
            return jsonify({"message": "Flow deleted"}), 200
        return jsonify({"error": "Flow not found"}), 404

@flows_bp.route('/flows/<flow_id>/executions', methods=['GET'])
def get_flow_execution_history(flow_id):
    """Get execution history for a flow"""
    limit = request.args.get('limit', 10, type=int)
    executions = get_flow_executions(flow_id, limit)
    return jsonify(executions)

# --- Component Management ---

@flows_bp.route('/components', methods=['GET'])
def list_tframex_studio_components():
    logger.info("Request received for /api/tframex/components")
    try:
        global_tframex_app = get_global_tframex_app()
        # Components are discovered from the global app instance
        components = discover_tframex_components(app_instance=global_tframex_app)
        return jsonify(components)
    except Exception as e:
        logger.error(f"Error discovering TFrameX components: {e}", exc_info=True)
        return jsonify({"error": "Failed to load TFrameX components from backend"}), 500

@flows_bp.route('/register_code', methods=['POST'])
@require_permission('flows.create')
def handle_register_tframex_code():
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    python_code = data.get("python_code")

    if not python_code:
        return jsonify({"error": "Missing 'python_code' in request"}), 400

    logger.info(f"Attempting to register new TFrameX component from user code (length: {len(python_code)}).")

    # Code is registered on the global app instance
    result = register_code_dynamically(python_code, app_instance_to_modify=global_tframex_app)

    if result["success"]:
        return jsonify({"success": True, "message": result["message"]}), 200
    else:
        return jsonify({"success": False, "error": result["message"]}), 500

# --- Flow Execution ---

@flows_bp.route('/flow/execute', methods=['POST'])
@require_permission('flows.execute')
def handle_execute_tframex_flow():
    global_tframex_app = get_global_tframex_app()
    run_id = f"sflw_{int(time.time())}_{os.urandom(3).hex()}"
    logger.info(f"--- API Call: /api/tframex/flow/execute (Run ID: {run_id}) ---")

    data = request.get_json()
    visual_nodes = data.get('nodes')
    visual_edges = data.get('edges')
    initial_input_content = data.get("initial_input", "Default starting message for the visual flow.")
    global_flow_template_vars = data.get("global_flow_template_vars", {})

    if not visual_nodes:
        logger.warning(f"Run ID {run_id}: No 'nodes' provided in flow execution request.")
        return jsonify({"output": f"Run ID {run_id}: Error - No visual nodes provided.", "error": "Missing 'nodes' in flow definition"}), 400

    execution_log = [f"--- TFrameX Visual Flow Execution Start (Run ID: {run_id}) ---"]

    # --- Create a temporary TFrameXApp instance for this specific run ---
    # v1.1.0: Include MCP configuration if available
    temp_run_app = TFrameXApp(
        default_llm=global_tframex_app.default_llm,
        mcp_config_file=None  # Don't reload MCP for temp instances
    )
    execution_log.append(f"  Created temporary TFrameXApp for run_id: {run_id}")

    # Re-register all globally known tools onto the temporary app instance
    # This ensures tools added dynamically via UI are available for this run
    if global_tframex_app._tools:
        execution_log.append(f"  Registering {len(global_tframex_app._tools)} global tools onto temporary app...")
        for tool_name, tool_obj in global_tframex_app._tools.items():
            try:
                # Re-register by calling the .tool() decorator method on the temp_run_app instance
                # Provide the JSON schema dictionary for parameters_schema,
                # as tool_obj.parameters (the Pydantic model class) seems to cause issues with '.get()'
                # In v1.1.0, parameters is a Pydantic model, use model_dump
                params_data_dict = tool_obj.parameters.model_dump(exclude_none=True) if tool_obj.parameters else None
                temp_run_app.tool(
                    name=tool_name,
                    description=tool_obj.description,
                    parameters_schema=params_data_dict # Pass the data dictionary
                )(tool_obj.func) # Call the returned decorator with the actual tool function
                execution_log.append(f"    - Tool '{tool_name}' registered on temporary app.")
            except Exception as e_tool_reg:
                error_msg = f"    - Failed to register tool '{tool_name}' on temporary app: {e_tool_reg}"
                logger.error(error_msg)
                execution_log.append(error_msg)
    else:
        execution_log.append("  No global tools to register on temporary app.")
    # --- End temporary app setup ---

    # 1. Translate visual graph to tframex.Flow, using the temporary app for registrations
    constructed_tframex_flow, translation_log_messages, _ = translate_visual_to_tframex_flow(
        flow_id=run_id,
        visual_nodes=visual_nodes,
        visual_edges=visual_edges,
        global_app_instance=global_tframex_app, # Source of base agent definitions
        current_run_app_instance=temp_run_app    # Target for this run's specific agent configs
    )
    execution_log.extend(translation_log_messages)

    if not constructed_tframex_flow:
        error_msg = f"Run ID {run_id}: Failed to translate visual graph into an executable TFrameX Flow."
        logger.error(error_msg)
        execution_log.append(f"\nFATAL ERROR: {error_msg}")
        return jsonify({"output": "\n".join(execution_log), "error": error_msg}), 500

    if not constructed_tframex_flow.steps:
        error_msg = f"Run ID {run_id}: Translated TFrameX Flow has no steps. Nothing to execute."
        logger.warning(error_msg)
        execution_log.append(f"\nWARNING: {error_msg}")
        return jsonify({"output": "\n".join(execution_log), "error": "No executable steps in the flow."}), 200

    execution_log.append(f"\nSuccessfully translated to TFrameX Flow: {constructed_tframex_flow.flow_name} with {len(constructed_tframex_flow.steps)} steps.")
    execution_log.append("TFrameX Flow Steps (Effective Names/Types on Temporary App):")
    for step in constructed_tframex_flow.steps:
        execution_log.append(f"  - {str(step)}") # `str(step)` should show agent name or pattern instance


    # 2. Execute the TFrameX Flow using the temporary app
    final_preview_link = None
    execution_id = None
    
    # Track execution in database if flow_id provided
    if data.get('flow_id'):
        execution_id = create_flow_execution(
            flow_id=data['flow_id'],
            input_data={'initial_input': initial_input_content, 'template_vars': global_flow_template_vars}
        )
    
    try:
        # v1.1.0: Use the temporary app for the run context
        async def execute_flow():
            # Register the flow with the temporary app before creating runtime context
            temp_run_app.register_flow(constructed_tframex_flow)
            
            async with temp_run_app.run_context() as rt:
                
                start_message = Message(role="user", content=str(initial_input_content))
                
                execution_log.append(f"\nRunning TFrameX Flow with initial input: '{start_message.content[:100]}...'")
                if global_flow_template_vars:
                     execution_log.append(f"Global Flow Template Variables: {global_flow_template_vars}")
                
                # Run the flow
                final_flow_context = await rt.run_flow(
                    constructed_tframex_flow,
                    start_message,
                    initial_shared_data={"studio_run_id": run_id},
                    flow_template_vars=global_flow_template_vars
                )
                return final_flow_context
        
        final_flow_context = asyncio.run(execute_flow())
        
        execution_log.append(f"\n--- TFrameX Flow Result (Run ID: {run_id}) ---")
        execution_log.append(f"Final Message Role: {final_flow_context.current_message.role}")
        execution_log.append(f"Final Message Content:\n{final_flow_context.current_message.content}")

        if final_flow_context.current_message.tool_calls:
            tool_calls_summary = json.dumps([tc.model_dump(exclude_none=True) for tc in final_flow_context.current_message.tool_calls], indent=2)
            execution_log.append(f"Final Message Tool Calls (if any, unhandled at flow end):\n{tool_calls_summary}")

        if final_flow_context.shared_data:
             shared_data_summary = {k: (str(v)[:200] + '...' if len(str(v)) > 200 else str(v)) for k,v in final_flow_context.shared_data.items()}
             execution_log.append(f"Final Flow Shared Data:\n{json.dumps(shared_data_summary, indent=2)}")

        if "studio_preview_url" in final_flow_context.shared_data:
            final_preview_link = final_flow_context.shared_data["studio_preview_url"]
            execution_log.append("\n--- Preview Link Detected ---")
            execution_log.append(f"PREVIEW_LINK::{final_preview_link}")
            logger.info(f"Run ID {run_id}: Preview link found in shared_data: {final_preview_link}")
        
        # Update execution status in database
        if execution_id:
            update_flow_execution(
                execution_id,
                status='completed',
                output_data={
                    'final_message': final_flow_context.current_message.content,
                    'shared_data': final_flow_context.shared_data
                }
            )

    except Exception as e:
        error_msg = f"Run ID {run_id}: Error during TFrameX flow execution: {e}"
        logger.error(error_msg, exc_info=True)
        execution_log.append(f"\nEXECUTION ERROR: {str(e)}")
        
        # Update execution status in database
        if execution_id:
            update_flow_execution(
                execution_id,
                status='failed',
                error_message=str(e)
            )
        
        # Include the full execution log for debugging
        return jsonify({"output": "\n".join(execution_log), "error": f"Flow execution runtime error: {e}"}), 500

    execution_log.append(f"\n--- TFrameX Visual Flow Execution End (Run ID: {run_id}) ---")
    logger.info(f"Run ID {run_id}: Flow execution finished.")
    # The temp_run_app and its registered components will go out of scope and be garbage collected.
    return jsonify({"output": "\n".join(execution_log)})