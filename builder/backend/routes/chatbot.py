# routes/chatbot.py
import asyncio
import json
import logging
from flask import Blueprint, request, jsonify
from tframex import Message

from component_manager import discover_tframex_components

logger = logging.getLogger("ChatbotAPI")

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/tframex')

def get_global_tframex_app():
    """Get the global TFrameX app instance"""
    from tframex_config import get_tframex_app_instance
    return get_tframex_app_instance()

async def execute_chatbot_logic(rt, user_message, template_vars):
    """Execute the two-agent chatbot logic"""
    # Step 1: ConversationalAssistant handles user message
    assistant_input = Message(role="user", content=user_message)
    assistant_response = await rt.call_agent(
        "ConversationalAssistant",
        assistant_input,
        template_vars=template_vars
    )
    
    # Ensure we have a valid response
    if not assistant_response or not assistant_response.content:
        logger.error("ConversationalAssistant returned empty response")
        return {
            "reply": "Sorry, I couldn't process your request. The assistant didn't respond.",
            "flow_update": None
        }, 200
    
    assistant_reply = assistant_response.content.strip()
    logger.info(f"ConversationalAssistant response: {assistant_reply[:200]}...")

    # Step 2: Check if assistant wants to modify the flow
    if "FLOW_INSTRUCTION:" in assistant_reply:
        # Extract the flow instruction
        instruction_part = assistant_reply.split("FLOW_INSTRUCTION:")[-1].strip()
        
        # Remove the flow instruction from the user-facing reply
        user_reply = assistant_reply.split("FLOW_INSTRUCTION:")[0].strip()
        
        logger.info(f"Flow instruction detected: {instruction_part[:100]}...")
        
        # Step 3: FlowBuilderAgent generates the flow JSON
        flow_template_vars = {
            **template_vars,
            "flow_instruction": instruction_part
        }
        
        flow_builder_input = Message(role="user", content="Generate ReactFlow JSON based on the instruction.")
        flow_builder_response = await rt.call_agent(
            "FlowBuilderAgent",
            flow_builder_input,
            template_vars=flow_template_vars
        )
        
        flow_json_content = flow_builder_response.content.strip()
        logger.info(f"FlowBuilderAgent response: {flow_json_content[:200]}...")
        
        # Step 4: Parse and validate the JSON
        flow_update_json = None
        try:
            # Handle markdown-wrapped JSON
            if flow_json_content.startswith("```json"):
                # Extract JSON from markdown code block
                start_idx = flow_json_content.find("```json") + 7
                end_idx = flow_json_content.find("```", start_idx)
                if end_idx != -1:
                    flow_json_content = flow_json_content[start_idx:end_idx].strip()
            elif flow_json_content.startswith("```"):
                # Extract JSON from generic code block
                start_idx = flow_json_content.find("```") + 3
                end_idx = flow_json_content.find("```", start_idx)
                if end_idx != -1:
                    flow_json_content = flow_json_content[start_idx:end_idx].strip()
            
            flow_update_json = json.loads(flow_json_content)
            
            if (isinstance(flow_update_json, dict) and
                "nodes" in flow_update_json and isinstance(flow_update_json.get("nodes"), list) and
                "edges" in flow_update_json and isinstance(flow_update_json.get("edges"), list)):
                
                logger.info("Successfully generated valid ReactFlow JSON structure.")
                return {
                    "reply": user_reply or "I've updated the flow based on your request. Please review the canvas.",
                    "flow_update": flow_update_json
                }, 200
            else:
                logger.warning(f"Flow builder returned JSON with invalid structure: {flow_json_content[:500]}...")
                return {
                    "reply": user_reply + "\n\nI tried to update the flow, but the structure wasn't quite right. Could you try rephrasing your request?",
                    "flow_update": None
                }, 200
                
        except json.JSONDecodeError as e:
            logger.error(f"Flow builder response was not valid JSON: {e}. Raw response: {flow_json_content[:1000]}...")
            return {
                "reply": user_reply + "\n\nI had trouble generating the flow update. Could you try rephrasing your request?",
                "flow_update": None
            }, 200
    else:
        # No flow modification requested, just return the conversational response
        return {
            "reply": assistant_reply,
            "flow_update": None
        }, 200

# Chatbot for building flows (using two-agent architecture)
@chatbot_bp.route('/chatbot_flow_builder', methods=['POST'])
def handle_tframex_chatbot_flow_builder():
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    user_message = data.get('message')
    current_nodes_json = data.get('nodes', [])
    current_edges_json = data.get('edges', [])

    if not user_message:
        return jsonify({"reply": "Error: No message provided to chatbot.", "flow_update": None}), 400

    logger.info(f"Chatbot flow builder request: '{user_message[:100]}...'")

    # 1. Prepare context for both agents
    available_components_data = discover_tframex_components(app_instance=global_tframex_app)

    ac_context_parts = ["Available TFrameX Components:"]
    for cat in ["agents", "patterns", "tools"]:
        ac_context_parts.append(f"\n{cat.upper()}:")
        for comp in available_components_data.get(cat, []):
            desc = comp.get('description', 'No description.')[:100]
            param_info = ""
            if cat == "patterns":
                param_info = f"(Params: {list(comp.get('constructor_params_schema', {}).keys())})"
            elif cat == "tools":
                param_info = f"(Params: {list(comp.get('parameters_schema', {}).get('properties', {}).keys())})"
            ac_context_parts.append(f"  - ID: {comp['id']}, Name: {comp['name']} {param_info}. Desc: {desc}...")
    available_components_context_str = "\n".join(ac_context_parts)

    current_flow_state_context_str = (
        f"Current Visual Flow State (Nodes: {len(current_nodes_json)}, Edges: {len(current_edges_json)}):\n"
        f"Nodes: {json.dumps(current_nodes_json, indent=2)}\n"
        f"Edges: {json.dumps(current_edges_json, indent=2)}"
    )

    # Check if both agents are registered
    if "ConversationalAssistant" not in global_tframex_app._agents:
        logger.error("Critical: ConversationalAssistant agent is not registered on global app.")
        return jsonify({"reply": "Error: Conversational assistant is not configured.", "flow_update": None}), 500
    
    if "FlowBuilderAgent" not in global_tframex_app._agents:
        logger.error("Critical: FlowBuilderAgent is not registered on global app.")
        return jsonify({"reply": "Error: Flow builder agent is not configured.", "flow_update": None}), 500

    template_vars = {
        "available_components_context": available_components_context_str,
        "current_flow_state_context": current_flow_state_context_str
    }

    try:
        # Two-agent architecture: Assistant -> FlowBuilder
        async def run_chatbot():
            async with global_tframex_app.run_context() as rt:
                return await execute_chatbot_logic(rt, user_message, template_vars)
        
        result_data, status_code = asyncio.run(run_chatbot())
        return jsonify(result_data), status_code
        
    except Exception as e:
        logger.error(f"Error in two-agent chatbot flow builder: {e}", exc_info=True)
        # Always return a valid JSON response structure
        return jsonify({
            "reply": f"Error processing your request: {str(e)}",
            "flow_update": None
        }), 200  # Use 200 to avoid triggering error handlers on frontend