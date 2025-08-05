# backend/component_manager.py
# builder/backend/component_manager.py
import inspect
import logging
import json # For robust parameter serialization
from tframex import patterns as tframex_patterns_module
from tframex.patterns import BasePattern
from tframex import ToolParameters, ToolParameterProperty

logger = logging.getLogger("ComponentManager")

def get_pattern_constructor_params_schema(pattern_class):
    """Inspects a Pattern class's __init__ method for configurable parameters."""
    params_schema = {}
    try:
        sig = inspect.signature(pattern_class.__init__)
        for name, param in sig.parameters.items():
            if name in ['self', 'pattern_name', 'args', 'kwargs']: # Common internal params
                continue
            
            param_type_str = "string" # Default
            if param.annotation != inspect.Parameter.empty:
                if hasattr(param.annotation, '__name__'):
                    param_type_str = param.annotation.__name__
                elif hasattr(param.annotation, '__origin__') and hasattr(param.annotation.__origin__, '__name__'): 
                    args_str = ", ".join([getattr(arg, '__name__', str(arg)) for arg in getattr(param.annotation, '__args__', [])])
                    param_type_str = f"{param.annotation.__origin__.__name__}[{args_str}]" if args_str else param.annotation.__origin__.__name__
                else:
                    param_type_str = str(param.annotation)

            default_value = "REQUIRED"
            if param.default != inspect.Parameter.empty:
                try: 
                    default_value = json.dumps(param.default)
                except TypeError:
                    default_value = str(param.default)


            params_schema[name] = {
                "type_hint": param_type_str,
                "default": default_value,
                "description": f"Parameter '{name}' for {pattern_class.__name__}. Type: {param_type_str}."
            }
    except Exception as e:
        logger.error(f"Error inspecting pattern {pattern_class.__name__}: {e}", exc_info=True)
    return params_schema

def discover_tframex_components(app_instance): # app_instance is now a required argument
    """
    Discovers available TFrameX agents, tools, and patterns from the given app_instance.
    Enhanced for v1.1.0 to include MCP tools and better categorization.
    Returns a dictionary structured for the frontend.
    """
    components = {"agents": [], "tools": [], "patterns": [], "mcp_servers": []}
    
    # Add static MCP Server component for users to create new servers
    components["mcp_servers"].append({
        "id": "mcp_server_new",
        "name": "MCP Server",
        "description": "Model Context Protocol server connection. Configure and connect to external data sources.",
        "component_category": "mcp_server",
        "config_options": {
            "supports_stdio": True,
            "supports_http": True,
            "requires_configuration": True
        }
    })

    # Discover Agents registered with the TFrameXApp instance
    for agent_name, reg_info in app_instance._agents.items():
        config = reg_info.get("config", {})
        agent_class_ref = config.get("agent_class_ref")
        agent_type_name = agent_class_ref.__name__ if agent_class_ref else "UnknownAgentType"
        
        # Check for MCP tool configurations (v1.1.0)
        mcp_tools_from_servers = config.get("mcp_tools_from_servers", None)
        
        components["agents"].append({
            "id": agent_name, 
            "name": agent_name, 
            "description": config.get("description", f"TFrameX {agent_type_name}: {agent_name}"),
            "component_category": "agent", 
            "tframex_agent_type": agent_type_name, 
            "config_options": { 
                "system_prompt_template": config.get("system_prompt_template", ""),
                "can_use_tools": config.get("can_use_tools", "LLMAgent" in agent_type_name or "ToolAgent" in agent_type_name),
                "default_tools": config.get("tool_names", []), 
                "can_call_agents": config.get("can_call_agents", "LLMAgent" in agent_type_name),
                "default_callable_agents": config.get("callable_agent_names", []),
                "strip_think_tags": config.get("strip_think_tags", False),
                "mcp_tools_from_servers": mcp_tools_from_servers,  # v1.1.0
                "max_tool_iterations": config.get("max_tool_iterations", 10),  # v1.1.0
            }
        })

    # Discover Tools registered with the TFrameXApp instance
    for tool_name, tool_obj in app_instance._tools.items():
        # Determine if this is an MCP tool (v1.1.0)
        is_mcp_tool = tool_name.startswith("tframex_") and "mcp" in tool_name
        is_external_mcp_tool = "__" in tool_name  # Format: server_alias__tool_name
        
        tool_info = {
            "id": tool_name,
            "name": tool_name,
            "description": tool_obj.description,
            "component_category": "tool",
            "parameters_schema": tool_obj.parameters.model_json_schema() if tool_obj.parameters else {},
            "config_options": {
                "has_data_output": bool(tool_obj.func.__annotations__.get('return') not in [None, inspect._empty]),
                "is_mcp_meta_tool": is_mcp_tool,
                "is_external_mcp_tool": is_external_mcp_tool,
            }
        }
        
        # Extract MCP server info if it's an external MCP tool
        if is_external_mcp_tool:
            server_alias = tool_name.split("__")[0]
            tool_info["config_options"]["mcp_server_alias"] = server_alias
        
        components["tools"].append(tool_info)
    
    # Discover Built-in Patterns from the tframex.patterns module
    for name, member in inspect.getmembers(tframex_patterns_module):
        if inspect.isclass(member) and issubclass(member, BasePattern) and member != BasePattern:
            components["patterns"].append({
                "id": name, 
                "name": name,
                "description": inspect.getdoc(member) or f"TFrameX Pattern: {name}",
                "component_category": "pattern",
                "constructor_params_schema": get_pattern_constructor_params_schema(member)
            })
    
    # Discover MCP Servers if available (v1.1.0)
    if hasattr(app_instance, '_mcp_manager') and app_instance._mcp_manager:
        try:
            # Access the connected servers from MCP manager
            if hasattr(app_instance._mcp_manager, '_connected_servers'):
                for server_alias, server_info in app_instance._mcp_manager._connected_servers.items():
                    # Extract capabilities
                    available_tools = []
                    available_resources = []
                    available_prompts = []
                    
                    if hasattr(server_info, 'tools') and server_info.tools:
                        available_tools = [{"name": tool.name, "description": getattr(tool, 'description', '')} 
                                         for tool in server_info.tools]
                    
                    if hasattr(server_info, 'resources') and server_info.resources:
                        available_resources = [{"name": resource.name} 
                                             for resource in server_info.resources]
                    
                    if hasattr(server_info, 'prompts') and server_info.prompts:
                        available_prompts = [{"name": prompt.name} 
                                           for prompt in server_info.prompts]
                    
                    components["mcp_servers"].append({
                        "id": f"mcp_server_{server_alias}",
                        "name": f"MCP Server: {server_alias}",
                        "description": f"Connected MCP server '{server_alias}' with {len(available_tools)} tools, {len(available_resources)} resources, {len(available_prompts)} prompts",
                        "component_category": "mcp_server",
                        "server_alias": server_alias,
                        "status": "connected",
                        "available_tools": available_tools,
                        "available_resources": available_resources,
                        "available_prompts": available_prompts
                    })
        except Exception as e:
            logger.warning(f"Could not discover MCP servers: {e}")
            
    return components

def register_code_dynamically(python_code: str, app_instance_to_modify): # app_instance is now a required argument
    """
    Executes user-provided Python code to register new TFrameX agents or tools
    on the provided app_instance_to_modify.
    Enhanced for v1.1.0 with additional imports and capabilities.
    The code *must* use the global 'tframex_app' for decorators within the exec scope.
    """
    logger.info(f"Attempting to dynamically register code. Current tools: {len(app_instance_to_modify._tools)}, agents: {len(app_instance_to_modify._agents)}")
    
    # Import all v1.1.0 components
    from tframex import (
        TFrameXApp, OpenAIChatLLM, Message, MessageChunk, BaseLLMWrapper,
        BaseAgent, LLMAgent, ToolAgent, Flow, FlowContext,
        Tool, ToolCall, FunctionCall, ToolDefinition, BaseMemoryStore, InMemoryMemoryStore,
        setup_logging
    )
    from tframex.patterns import (
        BasePattern, SequentialPattern, ParallelPattern, RouterPattern, DiscussionPattern
    )
    from tframex.mcp import MCPManager, MCPConnectedServer
    import os
    import asyncio
    import json as _json 
    import logging as _logging 
    from dotenv import load_dotenv as _load_dotenv
    from datetime import datetime
    from pathlib import Path

    # Critical: the 'tframex_app' in the exec scope must be the app_instance_to_modify
    exec_globals = {
        "tframex_app": app_instance_to_modify, 
        # Core TFrameX v1.1.0 components
        "TFrameXApp": TFrameXApp,
        "OpenAIChatLLM": OpenAIChatLLM,
        "Message": Message,
        "MessageChunk": MessageChunk,
        "BaseLLMWrapper": BaseLLMWrapper,
        "BaseAgent": BaseAgent,
        "LLMAgent": LLMAgent,
        "ToolAgent": ToolAgent,
        "Flow": Flow,
        "FlowContext": FlowContext,
        # Tool-related classes
        "Tool": Tool,
        "ToolCall": ToolCall,
        "FunctionCall": FunctionCall,
        "ToolDefinition": ToolDefinition,
        "ToolParameters": ToolParameters,
        "ToolParameterProperty": ToolParameterProperty,
        # Memory stores
        "BaseMemoryStore": BaseMemoryStore,
        "InMemoryMemoryStore": InMemoryMemoryStore,
        # Patterns
        "BasePattern": BasePattern,
        "SequentialPattern": SequentialPattern,
        "ParallelPattern": ParallelPattern,
        "RouterPattern": RouterPattern,
        "DiscussionPattern": DiscussionPattern,
        # MCP support
        "MCPManager": MCPManager,
        "MCPConnectedServer": MCPConnectedServer,
        # Utilities
        "setup_logging": setup_logging,
        "os": os,
        "asyncio": asyncio,
        "json": _json,
        "logging": _logging,
        "load_dotenv": _load_dotenv,
        "datetime": datetime,
        "Path": Path,
        "print": logger.info, 
    }

    try:
        exec(python_code, exec_globals, {}) 
        logger.info(f"Successfully executed user-provided code. New tools on modified app: {len(app_instance_to_modify._tools)}, agents: {len(app_instance_to_modify._agents)}")
        return {"success": True, "message": "Code executed and components potentially registered on the target app instance."}
    except Exception as e:
        logger.error(f"Error executing user-provided code: {e}", exc_info=True)
        return {"success": False, "message": f"Error executing code: {str(e)}"}