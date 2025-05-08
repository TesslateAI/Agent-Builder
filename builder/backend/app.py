# backend/app.py
import os
import asyncio
import json
import logging
from flask import Flask, request, jsonify, send_from_directory # Added send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# (Keep existing imports: run_flow, get_model, strip_think_tags, get_definitions...)
from flow_executor import run_flow, get_model, strip_think_tags
from agent_definitions import get_definitions_for_frontend, get_definition

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FlaskServer")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# Ensure base output directory for runs exists
GENERATED_DIR = "generated"
# (Keep existing directory creation logic, add GENERATED_DIR)
required_dirs = [
    "example_outputs",
    os.path.join("example_outputs", "ex4_multi_call_outputs"),
    GENERATED_DIR # Add the new base directory
]
for dir_path in required_dirs:
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
        except OSError as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")

# --- API Endpoints ---

@app.route('/')
def index():
    return "Backend is running. Use API endpoints."

# (Keep existing /api/agents, /api/run, /api/chatbot endpoints...)
@app.route('/api/agents', methods=['GET'])
def list_agents():
    # Keep existing logic...
    logger.info("Request received on /api/agents")
    try:
        definitions = get_definitions_for_frontend()
        return jsonify(definitions)
    except Exception as e:
        logger.error(f"Error getting agent definitions: {e}", exc_info=True)
        return jsonify({"error": "Failed to load agent definitions"}), 500

@app.route('/api/run', methods=['POST'])
async def handle_run_flow():
    # Keep existing logic...
    logger.info("Received request on /api/run")
    if not request.is_json:
        logger.warning("Request is not JSON")
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    nodes = data.get('nodes')
    edges = data.get('edges')
    if nodes is None or edges is None:
        logger.warning("Missing 'nodes' or 'edges' in request data")
        return jsonify({"error": "Missing 'nodes' or 'edges' in request data"}), 400

    logger.info(f"Received {len(nodes)} nodes and {len(edges)} edges for dynamic execution.")
    try:
        result_log = await run_flow(nodes, edges)
        logger.info("Dynamic flow execution completed.")
        return jsonify({"output": result_log})
    except RuntimeError as e:
         logger.error(f"Runtime error during flow execution: {e}", exc_info=True)
         return jsonify({"error": f"Runtime Error: {e}"}), 500
    except ImportError as e:
        logger.error(f"Import error, check agent definitions/imports: {e}", exc_info=True)
        return jsonify({"error": f"Import Error: {e}. Check backend agent setup."}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during flow execution: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/chatbot', methods=['POST'])
async def handle_chatbot():
    # Keep existing logic...
    logger.info("Received request on /api/chatbot")
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    user_message = data.get('message')
    current_nodes = data.get('nodes', [])
    current_edges = data.get('edges', [])
    available_defs_frontend = data.get('definitions', [])
    if not user_message: return jsonify({"error": "Missing 'message'"}), 400

    try:
        available_nodes_str = "\n".join([f"- ID: {d['id']}, Name: {d['name']}, Type: {d['type']}" for d in available_defs_frontend])
        current_flow_str = json.dumps({"nodes": current_nodes, "edges": current_edges}, indent=2)
        agent_id = "flowBuilderAgent"
        definition = get_definition(agent_id)
        if not definition or not definition.get('constructor') or not definition.get('execute_function'):
            logger.error(f"Flow Builder Agent ('{agent_id}') not defined correctly.")
            return jsonify({"reply": "Error: Chatbot agent is not configured.", "flow": None}), 500
        model = await get_model()
        agent_instance = definition['constructor'](model)
        input_payload = {
            "user_message": user_message,
            "available_nodes_context": available_nodes_str,
            "current_flow_context": current_flow_str
        }
        agent_result = await definition['execute_function'](agent_instance, input_payload)
        raw_output = agent_result.get('raw_llm_output', '')
        logger.debug(f"Raw Chatbot LLM Output:\n{raw_output}")
        json_string = strip_think_tags(raw_output)
        parsed_flow = None
        reply_message = "Sorry, I couldn't process your request properly."
        if json_string:
            try:
                parsed_data = json.loads(json_string)
                if isinstance(parsed_data, dict) and \
                   'nodes' in parsed_data and isinstance(parsed_data.get('nodes'), list) and \
                   'edges' in parsed_data and isinstance(parsed_data.get('edges'), list):
                    parsed_flow = parsed_data
                    reply_message = "Okay, I've updated the flow."
                    logger.info(f"Chatbot successfully generated a valid flow update.")
                else:
                    reply_message = "Sorry, the response wasn't in the expected flow format."
                    logger.warning(f"Chatbot output failed validation. Parsed type: {type(parsed_data)}")
            except json.JSONDecodeError as json_err:
                reply_message = "Sorry, my internal response was not valid JSON."
                logger.error(f"Chatbot output failed JSON parsing: {json_err}. String: {json_string}")
            except Exception as parse_err:
                 reply_message = f"Sorry, an error occurred processing the response: {parse_err}"
                 logger.error(f"Chatbot unexpected parsing error: {parse_err}", exc_info=True)
        else:
             reply_message = "Sorry, I received an empty response. Please try again."
             logger.warning("Chatbot returned empty string after stripping tags.")

        return jsonify({"reply": reply_message, "flow": parsed_flow})
    except RuntimeError as e:
         logger.error(f"Runtime error during chatbot request: {e}", exc_info=True)
         return jsonify({"reply": f"Server Runtime Error: {e}", "flow": None}), 500
    except Exception as e:
        logger.error(f"Unexpected error during chatbot request: {e}", exc_info=True)
        return jsonify({"reply": f"Unexpected server error: {e}", "flow": None}), 500


# --- NEW: Preview Route ---
@app.route('/api/preview/<run_id>/<path:filepath>')
def serve_generated_file(run_id, filepath):
    """Serves files from a specific run's generated folder."""
    logger.info(f"Request received for preview: run_id={run_id}, filepath={filepath}")
    # Security: Ensure run_id and filepath are safe path components
    # Basic check: ensure no '..' traversal
    if '..' in run_id or '..' in filepath:
        logger.warning(f"Potential path traversal detected in preview request: {run_id}/{filepath}")
        return "Invalid path", 404

    directory = os.path.abspath(os.path.join(GENERATED_DIR, run_id))

    # Security: Double-check the final directory path is within GENERATED_DIR
    if not directory.startswith(os.path.abspath(GENERATED_DIR)):
         logger.error(f"Attempt to access directory outside generated folder: {directory}")
         return "Access denied", 403

    # Check if the directory for the run_id exists
    if not os.path.isdir(directory):
        logger.error(f"Preview directory not found: {directory}")
        return "Run ID not found", 404

    logger.debug(f"Attempting to send file: {filepath} from directory: {directory}")
    try:
        return send_from_directory(directory, filepath)
    except FileNotFoundError:
        logger.error(f"File not found in preview request: {directory}/{filepath}")
        return "File not found", 404
    except Exception as e:
         logger.error(f"Error serving file {directory}/{filepath}: {e}", exc_info=True)
         return "Error serving file", 500
# --- END NEW ---


# --- Application Entry Point (Keep existing) ---
if __name__ == '__main__':
    # (Keep checks for agent definitions)
    try:
        defs = get_definitions_for_frontend()
        if not defs: logger.warning("Agent definitions list for frontend is empty.")
        else: logger.info(f"Loaded {len(defs)} agent/system definitions for frontend.")
        # Add check for the new agents if desired
        req_agents = {'plannerAgent', 'distributorAgent', 'fileGeneratorAgent'}
        loaded_agents = {d['id'] for d in defs}
        if not req_agents.issubset(loaded_agents):
             logger.warning(f"Missing one or more Software Builder agents: {req_agents - loaded_agents}")
    except Exception as e:
         logger.error(f"CRITICAL: Failed to load agent definitions: {e}", exc_info=True)

    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5001))
    debug = os.getenv('FLASK_ENV') == 'development'

    logger.info(f"Starting Flask server on {host}:{port} (Debug: {debug})")
    app.run(host=host, port=port, debug=debug)