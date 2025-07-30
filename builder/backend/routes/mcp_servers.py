# routes/mcp_servers.py
import logging
import asyncio
from flask import Blueprint, request, jsonify

logger = logging.getLogger("MCPServersAPI")

mcp_servers_bp = Blueprint('mcp_servers', __name__, url_prefix='/api/tframex/mcp')

def get_global_tframex_app():
    """Get the global TFrameX app instance"""
    from tframex_config import get_tframex_app_instance
    return get_tframex_app_instance()

@mcp_servers_bp.route('/status', methods=['GET'])
def get_mcp_status():
    """Get the status of MCP integration (v1.1.0 feature)"""
    logger.info("Request received for /api/tframex/mcp/status")
    try:
        global_tframex_app = get_global_tframex_app()
        mcp_status = {
            "enabled": False,
            "servers": [],
            "meta_tools": []
        }
        
        if hasattr(global_tframex_app, '_mcp_manager') and global_tframex_app._mcp_manager:
            mcp_status["enabled"] = True
            
            # Get connected servers
            if hasattr(global_tframex_app._mcp_manager, '_connected_servers'):
                for server_alias in global_tframex_app._mcp_manager._connected_servers:
                    mcp_status["servers"].append({
                        "alias": server_alias,
                        "status": "connected"
                    })
            
            # List MCP meta-tools
            mcp_meta_tool_names = [
                "tframex_list_mcp_servers",
                "tframex_list_mcp_resources", 
                "tframex_read_mcp_resource",
                "tframex_list_mcp_prompts",
                "tframex_use_mcp_prompt"
            ]
            for tool_name in mcp_meta_tool_names:
                if tool_name in global_tframex_app._tools:
                    mcp_status["meta_tools"].append(tool_name)
        
        return jsonify(mcp_status)
    except Exception as e:
        logger.error(f"Error getting MCP status: {e}", exc_info=True)
        return jsonify({"error": "Failed to get MCP status"}), 500

@mcp_servers_bp.route('/servers/connect', methods=['POST'])
def connect_mcp_server():
    """Connect to an MCP server"""
    logger.info("Request received for /api/tframex/mcp/servers/connect")
    try:
        global_tframex_app = get_global_tframex_app()
        data = request.get_json()
        server_alias = data.get('server_alias')
        command = data.get('command')
        args = data.get('args', [])
        env = data.get('env', {})
        
        if not server_alias or not command:
            return jsonify({
                "success": False,
                "message": "Server alias and command are required"
            }), 400
        
        # Check if MCP manager is available
        if not hasattr(global_tframex_app, '_mcp_manager') or not global_tframex_app._mcp_manager:
            return jsonify({
                "success": False,
                "message": "MCP manager is not initialized"
            }), 500
        
        # Create server config
        server_config = {
            server_alias: {
                "command": command,
                "args": args,
                "env": env
            }
        }
        
        async def connect_server():
            try:
                # Initialize the server using MCP manager
                await global_tframex_app._mcp_manager.initialize_servers(server_config)
                
                # Get server info
                if server_alias in global_tframex_app._mcp_manager._connected_servers:
                    connected_server = global_tframex_app._mcp_manager._connected_servers[server_alias]
                    
                    # Extract available capabilities
                    tools = []
                    resources = []
                    prompts = []
                    
                    if hasattr(connected_server, 'tools') and connected_server.tools:
                        tools = [{"name": tool.name, "description": tool.description} 
                                for tool in connected_server.tools]
                    
                    if hasattr(connected_server, 'resources') and connected_server.resources:
                        resources = [{"name": resource.name} 
                                   for resource in connected_server.resources]
                    
                    if hasattr(connected_server, 'prompts') and connected_server.prompts:
                        prompts = [{"name": prompt.name} 
                                 for prompt in connected_server.prompts]
                    
                    return {
                        "success": True,
                        "message": f"Successfully connected to MCP server '{server_alias}'",
                        "server_info": {
                            "alias": server_alias,
                            "status": "connected",
                            "tools": tools,
                            "resources": resources,
                            "prompts": prompts
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to connect to MCP server '{server_alias}'"
                    }
                    
            except Exception as e:
                logger.error(f"Error connecting to MCP server '{server_alias}': {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Connection failed: {str(e)}"
                }
        
        result = asyncio.run(connect_server())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in connect_mcp_server: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500

@mcp_servers_bp.route('/servers/disconnect', methods=['POST'])
def disconnect_mcp_server():
    """Disconnect from an MCP server"""
    logger.info("Request received for /api/tframex/mcp/servers/disconnect")
    try:
        global_tframex_app = get_global_tframex_app()
        data = request.get_json()
        server_alias = data.get('server_alias')
        
        if not server_alias:
            return jsonify({
                "success": False,
                "message": "Server alias is required"
            }), 400
        
        # Check if MCP manager is available
        if not hasattr(global_tframex_app, '_mcp_manager') or not global_tframex_app._mcp_manager:
            return jsonify({
                "success": False,
                "message": "MCP manager is not initialized"
            }), 500
        
        async def disconnect_server():
            try:
                # Check if server is connected
                if server_alias in global_tframex_app._mcp_manager._connected_servers:
                    connected_server = global_tframex_app._mcp_manager._connected_servers[server_alias]
                    
                    # Close the connection
                    if hasattr(connected_server, 'close'):
                        await connected_server.close()
                    
                    # Remove from connected servers
                    del global_tframex_app._mcp_manager._connected_servers[server_alias]
                    
                    return {
                        "success": True,
                        "message": f"Successfully disconnected from MCP server '{server_alias}'"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"MCP server '{server_alias}' is not connected"
                    }
                    
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server '{server_alias}': {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Disconnection failed: {str(e)}"
                }
        
        result = asyncio.run(disconnect_server())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in disconnect_mcp_server: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500

@mcp_servers_bp.route('/servers/<server_alias>/status', methods=['GET'])
def get_mcp_server_status(server_alias):
    """Get the status of a specific MCP server"""
    logger.info(f"Request received for /api/tframex/mcp/servers/{server_alias}/status")
    try:
        global_tframex_app = get_global_tframex_app()
        
        # Check if MCP manager is available
        if not hasattr(global_tframex_app, '_mcp_manager') or not global_tframex_app._mcp_manager:
            return jsonify({
                "success": False,
                "message": "MCP manager is not initialized"
            }), 500
        
        # Check if server is connected
        if server_alias in global_tframex_app._mcp_manager._connected_servers:
            connected_server = global_tframex_app._mcp_manager._connected_servers[server_alias]
            
            # Extract current capabilities
            tools = []
            resources = []
            prompts = []
            
            if hasattr(connected_server, 'tools') and connected_server.tools:
                tools = [{"name": tool.name, "description": tool.description} 
                        for tool in connected_server.tools]
            
            if hasattr(connected_server, 'resources') and connected_server.resources:
                resources = [{"name": resource.name} 
                           for resource in connected_server.resources]
            
            if hasattr(connected_server, 'prompts') and connected_server.prompts:
                prompts = [{"name": prompt.name} 
                         for prompt in connected_server.prompts]
            
            return jsonify({
                "success": True,
                "server_info": {
                    "alias": server_alias,
                    "status": "connected",
                    "tools": tools,
                    "resources": resources,
                    "prompts": prompts
                }
            })
        else:
            return jsonify({
                "success": True,
                "server_info": {
                    "alias": server_alias,
                    "status": "disconnected",
                    "tools": [],
                    "resources": [],
                    "prompts": []
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting MCP server status for '{server_alias}': {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500