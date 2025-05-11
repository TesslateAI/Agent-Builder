# backend/component_manager.py
# builder/backend/component_manager.py
import inspect
import logging
import json # For robust parameter serialization
from tframex import patterns as tframex_patterns_module
from tframex.patterns import BasePattern
# from tframex_config import get_tframex_app_instance # No longer needed here if app_instance is passed

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
    Returns a dictionary structured for the frontend.
    """
    # app = get_tframex_app_instance() # Use passed instance
    components = {"agents": [], "tools": [], "patterns": []}

    # Discover Agents registered with the TFrameXApp instance
    for agent_name, reg_info in app_instance._agents.items():
        config = reg_info.get("config", {})
        agent_class_ref = config.get("agent_class_ref")
        agent_type_name = agent_class_ref.__name__ if agent_class_ref else "UnknownAgentType"
        
        components["agents"].append({
            "id": agent_name, 
            "name": agent_name, 
            "description": config.get("description", f"TFrameX {agent_type_name}: {agent_name}"),
            "component_category": "agent", 
            "tframex_agent_type": agent_type_name, 
            "config_options": { 
                "system_prompt_template": config.get("system_prompt_template", ""),
                "can_use_tools": "LLMAgent" in agent_type_name or "ToolAgent" in agent_type_name, # LLMAgents and ToolAgents can use tools
                "default_tools": config.get("tool_names", []), 
                "can_call_agents": "LLMAgent" in agent_type_name,
                "default_callable_agents": config.get("callable_agent_names", []),
                "strip_think_tags": config.get("strip_think_tags", False),
            }
        })

    # Discover Tools registered with the TFrameXApp instance
    for tool_name, tool_obj in app_instance._tools.items():
        components["tools"].append({
            "id": tool_name,
            "name": tool_name,
            "description": tool_obj.description,
            "component_category": "tool",
            "parameters_schema": tool_obj.parameters.model_json_schema() if tool_obj.parameters else {},
             # Indicate if tool likely produces data for UI hints
            "config_options": {
                 "has_data_output": bool(tool_obj.func.__annotations__.get('return') not in [None, inspect._empty])
            }
        })
    
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
            
    return components

def register_code_dynamically(python_code: str, app_instance_to_modify): # app_instance is now a required argument
    """
    Executes user-provided Python code to register new TFrameX agents or tools
    on the provided app_instance_to_modify.
    The code *must* use the global 'tframex_app' for decorators within the exec scope.
    """
    # app = get_tframex_app_instance() # Use passed instance
    logger.info(f"Attempting to dynamically register code. Current tools: {len(app_instance_to_modify._tools)}, agents: {len(app_instance_to_modify._agents)}")
    
    from tframex import TFrameXApp, OpenAIChatLLM, Message, BaseLLMWrapper
    from tframex import BaseAgent, LLMAgent, ToolAgent 
    from tframex import Flow 
    from tframex.patterns import SequentialPattern, ParallelPattern, RouterPattern, DiscussionPattern 
    import os
    import asyncio
    import json as _json 
    import logging as _logging 
    from dotenv import load_dotenv as _load_dotenv

    # Critical: the 'tframex_app' in the exec scope must be the app_instance_to_modify
    exec_globals = {
        "tframex_app": app_instance_to_modify, 
        "TFrameXApp": TFrameXApp,
        "OpenAIChatLLM": OpenAIChatLLM,
        "Message": Message,
        "BaseLLMWrapper": BaseLLMWrapper,
        "BaseAgent": BaseAgent,
        "LLMAgent": LLMAgent,
        "ToolAgent": ToolAgent,
        "Flow": Flow,
        "SequentialPattern": SequentialPattern,
        "ParallelPattern": ParallelPattern,
        "RouterPattern": RouterPattern,
        "DiscussionPattern": DiscussionPattern,
        "os": os,
        "asyncio": asyncio,
        "json": _json,
        "logging": _logging,
        "load_dotenv": _load_dotenv,
        "print": logger.info, 
    }

    try:
        exec(python_code, exec_globals, {}) 
        logger.info(f"Successfully executed user-provided code. New tools on modified app: {len(app_instance_to_modify._tools)}, agents: {len(app_instance_to_modify._agents)}")
        return {"success": True, "message": "Code executed and components potentially registered on the target app instance."}
    except Exception as e:
        logger.error(f"Error executing user-provided code: {e}", exc_info=True)
        return {"success": False, "message": f"Error executing code: {str(e)}"}