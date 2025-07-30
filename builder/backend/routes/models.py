# routes/models.py
import logging
import time
import asyncio
from flask import Blueprint, request, jsonify
from tframex import OpenAIChatLLM, Message

logger = logging.getLogger("ModelsAPI")

# Model configuration storage (in-memory for now, can be moved to database later)
MODEL_CONFIGS = {}

def init_default_model():
    """Initialize default model configuration"""
    import os
    MODEL_CONFIGS['default'] = {
        'id': 'default',
        'name': 'Default Model',
        'provider': 'openai',
        'model_name': os.getenv("OPENAI_MODEL_NAME") or os.getenv("LLAMA_MODEL") or "gpt-3.5-turbo",
        'api_key': os.getenv("OPENAI_API_KEY") or os.getenv("LLAMA_API_KEY") or "ollama",
        'base_url': os.getenv("OPENAI_API_BASE") or os.getenv("LLAMA_BASE_URL") or "http://localhost:11434/v1",
        'is_default': True
    }

models_bp = Blueprint('models', __name__, url_prefix='/api/tframex/models')

@models_bp.route('', methods=['GET'])
def get_models():
    """Get all configured models"""
    logger.info("Request received for /api/tframex/models")
    try:
        models = list(MODEL_CONFIGS.values())
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"Error getting models: {e}", exc_info=True)
        return jsonify({"error": "Failed to get models"}), 500

@models_bp.route('', methods=['POST'])
def add_model():
    """Add a new model configuration"""
    logger.info("Request received to add model")
    try:
        data = request.json
        required_fields = ['name', 'provider', 'model_name', 'api_key', 'base_url']
        
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate unique ID
        model_id = f"model_{len(MODEL_CONFIGS)}_{int(time.time())}"
        
        # Create model config
        model_config = {
            'id': model_id,
            'name': data['name'],
            'provider': data['provider'],
            'model_name': data['model_name'],
            'api_key': data['api_key'],
            'base_url': data['base_url'],
            'is_default': False,
            'temperature': data.get('temperature', 0.7),
            'max_tokens': data.get('max_tokens', 2000)
        }
        
        MODEL_CONFIGS[model_id] = model_config
        logger.info(f"Added model configuration: {model_id}")
        
        return jsonify({"model": model_config}), 201
    except Exception as e:
        logger.error(f"Error adding model: {e}", exc_info=True)
        return jsonify({"error": "Failed to add model"}), 500

@models_bp.route('/<model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete a model configuration"""
    logger.info(f"Request received to delete model: {model_id}")
    try:
        if model_id not in MODEL_CONFIGS:
            return jsonify({"error": "Model not found"}), 404
        
        if MODEL_CONFIGS[model_id].get('is_default'):
            return jsonify({"error": "Cannot delete default model"}), 400
        
        del MODEL_CONFIGS[model_id]
        logger.info(f"Deleted model configuration: {model_id}")
        
        return jsonify({"message": "Model deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting model: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete model"}), 500

@models_bp.route('/<model_id>/default', methods=['PUT'])
def set_default_model(model_id):
    """Set a model as default"""
    logger.info(f"Request received to set default model: {model_id}")
    try:
        if model_id not in MODEL_CONFIGS:
            return jsonify({"error": "Model not found"}), 404
        
        # Remove default from all models
        for mid, config in MODEL_CONFIGS.items():
            config['is_default'] = False
        
        # Set new default
        MODEL_CONFIGS[model_id]['is_default'] = True
        logger.info(f"Set default model: {model_id}")
        
        return jsonify({"model": MODEL_CONFIGS[model_id]}), 200
    except Exception as e:
        logger.error(f"Error setting default model: {e}", exc_info=True)
        return jsonify({"error": "Failed to set default model"}), 500

@models_bp.route('/test', methods=['POST'])
def test_model():
    """Test a model configuration by making a simple API call"""
    logger.info("Request received to test model")
    try:
        data = request.json
        required_fields = ['provider', 'model_name', 'api_key', 'base_url']
        
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Try to create an LLM instance and make a simple test call
        try:
            test_llm = OpenAIChatLLM(
                model_name=data['model_name'],
                api_base_url=data['base_url'],
                api_key=data['api_key'],
                parse_text_tool_calls=True
            )
            
            # Make a simple test call
            async def test_call():
                response = await test_llm.chat_completion(
                    messages=[Message(role="user", content="Say 'test successful' in 3 words or less")],
                    stream=False,
                    max_tokens=10
                )
                return response.content if hasattr(response, 'content') else str(response)
            
            result = asyncio.run(test_call())
            
            return jsonify({
                "success": True,
                "message": "Model configuration is valid",
                "response": result
            }), 200
            
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            return jsonify({
                "success": False,
                "error": f"Model test failed: {str(e)}"
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing model: {e}", exc_info=True)
        return jsonify({"error": "Failed to test model"}), 500

def get_model_configs():
    """Get the MODEL_CONFIGS dictionary for use by other modules"""
    return MODEL_CONFIGS