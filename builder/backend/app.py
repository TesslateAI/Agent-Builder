
# backend/app.py
import os
import logging
import time
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# TFrameX v1.1.0 core components
from tframex import (
    setup_logging
)

# Import all blueprints
from routes.models import models_bp, init_default_model
from routes.mcp_servers import mcp_servers_bp  
from routes.flows import flows_bp
from routes.chatbot import chatbot_bp
from routes.files import files_bp, init_generated_files_dir
from routes.auth import auth_bp
from routes.health import health_bp

# Import authentication middleware
from middleware.auth import JWTMiddleware

# Initialize TFrameX App on startup
from tframex_config import get_tframex_app_instance

load_dotenv()

# Use TFrameX's setup_logging for consistency
setup_logging(level=logging.DEBUG, use_colors=True)
logger = logging.getLogger("FlaskTFrameXStudio")

def create_app():
    """Application factory pattern"""
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
    
    # Configure CORS for development and production
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",  # Vite dev server
                "http://127.0.0.1:5173",
                "http://localhost:5000",  # Production
                "http://127.0.0.1:5000"
            ],
            "supports_credentials": True,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize components
    init_default_model()
    init_generated_files_dir()
    
    # Initialize JWT middleware
    jwt_middleware = JWTMiddleware()
    jwt_middleware.init_app(app)
    
    # Initialize TFrameX App (this ensures it's created before blueprints use it)
    get_tframex_app_instance()
    
    # Initialize MCP in async context if it was deferred
    import asyncio
    from tframex_config import init_deferred_mcp
    
    async def setup_mcp():
        """Initialize MCP in async context."""
        try:
            mcp_success = await init_deferred_mcp()
            if mcp_success:
                logger.info("MCP initialization completed successfully")
            else:
                logger.info("MCP initialization skipped or failed")
        except Exception as e:
            logger.error(f"Error during MCP setup: {e}")
    
    # Run MCP setup in new event loop if needed
    try:
        # Try to get existing loop
        asyncio.get_running_loop()
        # If we have a loop, schedule MCP init
        asyncio.ensure_future(setup_mcp())
    except RuntimeError:
        # No loop running, create one for MCP init
        asyncio.run(setup_mcp())

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(mcp_servers_bp)
    app.register_blueprint(flows_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(files_bp)

    # Basic routes
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Docker"""
        return jsonify({"status": "healthy", "timestamp": time.time()}), 200

    @app.route('/')
    def index():
        """Serve the frontend in production, or API status in development"""
        frontend_dist = os.path.join(os.path.dirname(__file__), '../frontend/dist/index.html')
        if os.path.exists(frontend_dist):
            return send_from_directory('../frontend/dist', 'index.html')
        return jsonify({
            "status": "running",
            "message": "TFrameX Agent-Builder Backend API",
            "version": "1.0.0",
            "tframex_version": "1.1.0",
            "endpoints": [
                "/api/tframex/components",
                "/api/tframex/mcp/status",
                "/api/tframex/register_code",
                "/api/tframex/flow/execute",
                "/api/tframex/chatbot_flow_builder",
                "/api/tframex/models"
            ]
        })

    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files in production"""
        if path.startswith('api/'):
            return jsonify({"error": "Not found"}), 404
        frontend_dist = os.path.join(os.path.dirname(__file__), '../frontend/dist')
        if os.path.exists(os.path.join(frontend_dist, path)):
            return send_from_directory('../frontend/dist', path)
        # For SPA routing, return index.html for non-existent paths
        return send_from_directory('../frontend/dist', 'index.html')

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    # Configuration from environment
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV', 'development').lower() == 'development'
    
    # Log startup information
    logger.info("Starting Agent-Builder Backend")
    logger.info(f"Host: {host}:{port}")
    logger.info(f"Debug: {debug_mode}")
    logger.info("TFrameX Version: 1.1.0")
    
    # Check if frontend is built
    frontend_dist = os.path.join(os.path.dirname(__file__), '../frontend/dist/index.html')
    if os.path.exists(frontend_dist):
        logger.info("Frontend build detected - serving static files")
    else:
        logger.info("No frontend build found - API only mode")
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        use_reloader=False  # Disable reloader in async context
    )