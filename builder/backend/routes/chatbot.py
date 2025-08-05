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
    """Execute the orchestrator-based chatbot logic"""
    # Step 1: OrchestratorAgent handles user message (with tool calling capabilities)
    orchestrator_input = Message(role="user", content=user_message)
    orchestrator_response = await rt.call_agent(
        "OrchestratorAgent",
        orchestrator_input,
        template_vars=template_vars
    )
    
    # Ensure we have a valid response
    if not orchestrator_response or not orchestrator_response.content:
        logger.error("OrchestratorAgent returned empty response")
        return {
            "reply": "Sorry, I couldn't process your request. The orchestrator didn't respond.",
            "flow_update": None
        }, 200
    
    orchestrator_reply = orchestrator_response.content.strip()
    logger.info(f"OrchestratorAgent response: {orchestrator_reply[:200]}...")

    # Step 2: Check if orchestrator wants to modify the flow
    if "FLOW_INSTRUCTION:" in orchestrator_reply:
        # Extract the flow instruction
        instruction_part = orchestrator_reply.split("FLOW_INSTRUCTION:")[-1].strip()
        
        # Remove the flow instruction from the user-facing reply
        user_reply = orchestrator_reply.split("FLOW_INSTRUCTION:")[0].strip()
        
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
        logger.info("=== FlowBuilderAgent Output ===")
        logger.info(f"Instruction: {instruction_part[:100]}...")
        logger.info(f"Response length: {len(flow_json_content)} characters")
        logger.info(f"Raw output: {flow_json_content}")
        logger.info("=== End FlowBuilderAgent Output ===")
        
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
                logger.info(f"Nodes count: {len(flow_update_json.get('nodes', []))}")
                logger.info(f"Edges count: {len(flow_update_json.get('edges', []))}")
                
                # Log each node for debugging
                for i, node in enumerate(flow_update_json.get('nodes', [])):
                    logger.info(f"Node {i+1}: id={node.get('id')}, type={node.get('type')}, pos={node.get('position')}")
                
                # Log each edge for debugging  
                for i, edge in enumerate(flow_update_json.get('edges', [])):
                    logger.info(f"Edge {i+1}: {edge.get('source')} -> {edge.get('target')} (id={edge.get('id')})")
                
                
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
            "reply": orchestrator_reply,
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
    if "OrchestratorAgent" not in global_tframex_app._agents:
        logger.error("Critical: OrchestratorAgent is not registered on global app.")
        return jsonify({"reply": "Error: Orchestrator agent is not configured.", "flow_update": None}), 500
    
    if "FlowBuilderAgent" not in global_tframex_app._agents:
        logger.error("Critical: FlowBuilderAgent is not registered on global app.")
        return jsonify({"reply": "Error: Flow builder agent is not configured.", "flow_update": None}), 500

    template_vars = {
        "available_components_context": available_components_context_str,
        "current_flow_state_context": current_flow_state_context_str
    }

    try:
        # Two-agent architecture: Orchestrator -> FlowBuilder
        async def run_chatbot():
            async with global_tframex_app.run_context() as rt:
                return await execute_chatbot_logic(rt, user_message, template_vars)
        
        result_data, status_code = asyncio.run(run_chatbot())
        return jsonify(result_data), status_code
        
    except Exception as e:
        logger.error(f"Error in orchestrator-based chatbot flow builder: {e}", exc_info=True)
        # Always return a valid JSON response structure
        return jsonify({
            "reply": f"Error processing your request: {str(e)}",
            "flow_update": None
        }), 200  # Use 200 to avoid triggering error handlers on frontend


# Orchestrator Agent endpoints for flow analysis and optimization
@chatbot_bp.route('/orchestrator/analyze', methods=['POST'])
def orchestrator_analyze_flow():
    """Analyze flow structure using OrchestratorAgent"""
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    
    current_nodes = data.get('nodes', [])
    current_edges = data.get('edges', [])
    analysis_request = data.get('request', 'Analyze this flow structure')
    
    if not current_nodes:
        return jsonify({"error": "No nodes provided for analysis"}), 400
    
    logger.info(f"Orchestrator analysis request for {len(current_nodes)} nodes, {len(current_edges)} edges")
    
    # Check if OrchestratorAgent is registered
    if "OrchestratorAgent" not in global_tframex_app._agents:
        logger.error("OrchestratorAgent is not registered")
        return jsonify({"error": "OrchestratorAgent is not configured"}), 500
    
    try:
        async def run_analysis():
            async with global_tframex_app.run_context() as rt:
                # Prepare context for OrchestratorAgent
                available_components_data = discover_tframex_components(app_instance=global_tframex_app)
                
                template_vars = {
                    "available_components_context": _format_components_context(available_components_data),
                    "current_flow_state_context": _format_flow_state_context(current_nodes, current_edges)
                }
                
                message = f"{analysis_request}. Current flow has {len(current_nodes)} nodes and {len(current_edges)} edges."
                input_message = Message(role="user", content=message)
                
                response = await rt.call_agent(
                    "OrchestratorAgent",
                    input_message,
                    template_vars=template_vars
                )
                
                return response.content if response else "Analysis failed"
        
        analysis_result = asyncio.run(run_analysis())
        
        return jsonify({
            "analysis": analysis_result,
            "node_count": len(current_nodes),
            "edge_count": len(current_edges)
        })
        
    except Exception as e:
        logger.error(f"Error in orchestrator analysis: {e}", exc_info=True)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@chatbot_bp.route('/orchestrator/predict', methods=['POST'])
def orchestrator_predict_components():
    """Predict next components using OrchestratorAgent"""
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    
    current_nodes = data.get('nodes', [])
    current_edges = data.get('edges', [])
    user_intent = data.get('intent', 'What should I add next?')
    
    logger.info(f"Orchestrator prediction request: '{user_intent[:50]}...'")
    
    if "OrchestratorAgent" not in global_tframex_app._agents:
        return jsonify({"error": "OrchestratorAgent is not configured"}), 500
    
    try:
        async def run_prediction():
            async with global_tframex_app.run_context() as rt:
                available_components_data = discover_tframex_components(app_instance=global_tframex_app)
                
                template_vars = {
                    "available_components_context": _format_components_context(available_components_data),
                    "current_flow_state_context": _format_flow_state_context(current_nodes, current_edges)
                }
                
                message = f"Predict what components should be added next to this flow. User intent: {user_intent}"
                input_message = Message(role="user", content=message)
                
                response = await rt.call_agent(
                    "OrchestratorAgent",
                    input_message,
                    template_vars=template_vars
                )
                
                return response.content if response else "Prediction failed"
        
        prediction_result = asyncio.run(run_prediction())
        
        return jsonify({
            "predictions": prediction_result,
            "current_state": {
                "nodes": len(current_nodes),
                "edges": len(current_edges)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in orchestrator prediction: {e}", exc_info=True)
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@chatbot_bp.route('/orchestrator/optimize', methods=['POST'])
def orchestrator_optimize_flow():
    """Get flow optimization suggestions using OrchestratorAgent"""
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    
    current_nodes = data.get('nodes', [])
    current_edges = data.get('edges', [])
    optimization_goals = data.get('goals', ['performance', 'maintainability'])
    
    if not current_nodes:
        return jsonify({"error": "No nodes provided for optimization"}), 400
    
    logger.info(f"Orchestrator optimization request for {len(current_nodes)} nodes with goals: {optimization_goals}")
    
    if "OrchestratorAgent" not in global_tframex_app._agents:
        return jsonify({"error": "OrchestratorAgent is not configured"}), 500
    
    try:
        async def run_optimization():
            async with global_tframex_app.run_context() as rt:
                available_components_data = discover_tframex_components(app_instance=global_tframex_app)
                
                template_vars = {
                    "available_components_context": _format_components_context(available_components_data),
                    "current_flow_state_context": _format_flow_state_context(current_nodes, current_edges)
                }
                
                message = f"Optimize this flow for: {', '.join(optimization_goals)}. Provide specific suggestions."
                input_message = Message(role="user", content=message)
                
                response = await rt.call_agent(
                    "OrchestratorAgent", 
                    input_message,
                    template_vars=template_vars
                )
                
                return response.content if response else "Optimization failed"
        
        optimization_result = asyncio.run(run_optimization())
        
        return jsonify({
            "optimizations": optimization_result,
            "goals": optimization_goals,
            "analyzed_flow": {
                "nodes": len(current_nodes),
                "edges": len(current_edges)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in orchestrator optimization: {e}", exc_info=True)
        return jsonify({"error": f"Optimization failed: {str(e)}"}), 500


def _format_components_context(components_data):
    """Helper to format available components context"""
    context_parts = ["Available TFrameX Components:"]
    for cat in ["agents", "patterns", "tools"]:
        context_parts.append(f"\n{cat.upper()}:")
        for comp in components_data.get(cat, []):
            desc = comp.get('description', 'No description.')[:100]
            param_info = ""
            if cat == "patterns":
                param_info = f"(Params: {list(comp.get('constructor_params_schema', {}).keys())})"
            elif cat == "tools":
                param_info = f"(Params: {list(comp.get('parameters_schema', {}).get('properties', {}).keys())})"
            context_parts.append(f"  - ID: {comp['id']}, Name: {comp['name']} {param_info}. Desc: {desc}...")
    return "\n".join(context_parts)


def _format_flow_state_context(nodes, edges):
    """Helper to format current flow state context"""
    return (
        f"Current Visual Flow State (Nodes: {len(nodes)}, Edges: {len(edges)}):\n"
        f"Nodes: {json.dumps(nodes, indent=2)}\n"
        f"Edges: {json.dumps(edges, indent=2)}"
    )


@chatbot_bp.route('/orchestrator/test', methods=['POST'])
def orchestrator_test():
    """Test OrchestratorAgent functionality"""
    global_tframex_app = get_global_tframex_app()
    data = request.get_json()
    
    test_message = data.get('message', 'Hello OrchestratorAgent! Can you use your Flow Structure Analyzer tool to analyze an empty flow?')
    
    logger.info(f"Orchestrator test request: '{test_message[:100]}...'")
    
    if "OrchestratorAgent" not in global_tframex_app._agents:
        return jsonify({
            "error": "OrchestratorAgent is not registered", 
            "registered_agents": list(global_tframex_app._agents.keys())
        }), 500
    
    try:
        async def run_test():
            async with global_tframex_app.run_context() as rt:
                # Test basic functionality with simple context
                template_vars = {
                    "available_components_context": "Test Components: ConversationalAssistant, FlowBuilderAgent, OrchestratorAgent",
                    "current_flow_state_context": "Empty flow with 0 nodes and 0 edges"
                }
                
                input_message = Message(role="user", content=test_message)
                
                response = await rt.call_agent(
                    "OrchestratorAgent",
                    input_message,
                    template_vars=template_vars
                )
                
                return {
                    "success": True,
                    "response": response.content if response else "No response",
                    "agent_info": {
                        "name": "OrchestratorAgent",
                        "tools_available": len(global_tframex_app._tools),
                        "registered": True
                    }
                }
        
        result = asyncio.run(run_test())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in orchestrator test: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Test failed: {str(e)}",
            "agent_info": {
                "name": "OrchestratorAgent", 
                "registered": "OrchestratorAgent" in global_tframex_app._agents,
                "tools_count": len(global_tframex_app._tools)
            }
        }), 500