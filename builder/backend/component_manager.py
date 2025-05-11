# builder/backend/component_manager.py
import inspect
import logging
import json # For robust parameter serialization
from tframex import patterns as tframex_patterns_module
from tframex.patterns import BasePattern
from tframex_config import get_tframex_app_instance

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
                # Try to get a more descriptive type string
                if hasattr(param.annotation, '__name__'):
                    param_type_str = param.annotation.__name__
                elif hasattr(param.annotation, '__origin__') and hasattr(param.annotation.__origin__, '__name__'): # For List[str] etc.
                    args_str = ", ".join([getattr(arg, '__name__', str(arg)) for arg in getattr(param.annotation, '__args__', [])])
                    param_type_str = f"{param.annotation.__origin__.__name__}[{args_str}]" if args_str else param.annotation.__origin__.__name__
                else:
                    param_type_str = str(param.annotation)

            default_value = "REQUIRED"
            if param.default != inspect.Parameter.empty:
                try: # Serialize default value if it's not a simple type
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

def discover_tframex_components():
    """
    Discovers available TFrameX agents, tools, and patterns.
    Returns a dictionary structured for the frontend.
    """
    app = get_tframex_app_instance()
    components = {"agents": [], "tools": [], "patterns": []}

    # Discover Agents registered with the TFrameXApp instance
    for agent_name, reg_info in app._agents.items():
        config = reg_info.get("config", {})
        agent_class_ref = config.get("agent_class_ref")
        agent_type_name = agent_class_ref.__name__ if agent_class_ref else "UnknownAgentType"
        
        # Parameters for agents are less about __init__ and more about their specific needs
        # (e.g., system_prompt override, selected_tools, template_vars).
        # These will be handled by the agent node UI itself.
        components["agents"].append({
            "id": agent_name, # Use TFrameX registered name as ID
            "name": agent_name, # Or a display name if available in config.get("name")
            "description": config.get("description", f"TFrameX {agent_type_name}: {agent_name}"),
            "component_category": "agent", # For frontend filtering
            "tframex_agent_type": agent_type_name, # e.g., "LLMAgent", "ToolAgent"
            "config_options": { # Info to help frontend build UI for this agent node
                "system_prompt_template": config.get("system_prompt_template", ""),
                "can_use_tools": "LLMAgent" in agent_type_name, # LLMAgents can use tools
                "default_tools": config.get("tool_names", []), # Tools defined in @app.agent
                "can_call_agents": "LLMAgent" in agent_type_name,
                "default_callable_agents": config.get("callable_agent_names", []),
                "strip_think_tags": config.get("strip_think_tags", False),
                # Add other relevant config flags like 'llm_instance_override' presence
            }
        })

    # Discover Tools registered with the TFrameXApp instance
    for tool_name, tool_obj in app._tools.items():
        components["tools"].append({
            "id": tool_name,
            "name": tool_name,
            "description": tool_obj.description,
            "component_category": "tool",
            "parameters_schema": tool_obj.parameters.model_dump(exclude_none=True) if tool_obj.parameters else {},
        })
    
    # Discover Built-in Patterns from the tframex.patterns module
    for name, member in inspect.getmembers(tframex_patterns_module):
        if inspect.isclass(member) and issubclass(member, BasePattern) and member != BasePattern:
            components["patterns"].append({
                "id": name, # Class name, e.g., "SequentialPattern"
                "name": name,
                "description": inspect.getdoc(member) or f"TFrameX Pattern: {name}",
                "component_category": "pattern",
                "constructor_params_schema": get_pattern_constructor_params_schema(member)
            })
            
    return components

def register_code_dynamically(python_code: str):
    """
    Executes user-provided Python code to register new TFrameX agents or tools.
    The code *must* use the global 'tframex_app_instance' for decorators.
    """
    app = get_tframex_app_instance()
    logger.info(f"Attempting to dynamically register code. Current tools: {len(app._tools)}, agents: {len(app._agents)}")
    
    # Prepare the execution scope
    # Import common modules and TFrameX components that user code might need
    from tframex import TFrameXApp, OpenAIChatLLM, Message, BaseLLMWrapper
    from tframex import BaseAgent, LLMAgent, ToolAgent # Agent base classes
    from tframex import Flow # Flow class
    from tframex.patterns import SequentialPattern, ParallelPattern, RouterPattern, DiscussionPattern # Patterns
    import os
    import asyncio
    import json as _json # Avoid conflict if user code also uses 'json'
    import logging as _logging # Avoid conflict
    from dotenv import load_dotenv as _load_dotenv

    exec_globals = {
        "tframex_app": app, # Crucial: Make the app instance available for decorators
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
        "print": logger.info, # Redirect print to logger for visibility from user code
        # You can add more common imports here
    }
    # Also provide access to already registered components in case the user code refers to them
    # e.g., if defining an agent that calls another already registered agent by name.
    # This is implicitly handled as TFrameXApp resolves names at runtime.

    try:
        exec(python_code, exec_globals, {}) # Execute in a fresh local scope that can see exec_globals
        logger.info(f"Successfully executed user-provided code. New tools: {len(app._tools)}, agents: {len(app._agents)}")
        return {"success": True, "message": "Code executed and components potentially registered."}
    except Exception as e:
        logger.error(f"Error executing user-provided code: {e}", exc_info=True)
        return {"success": False, "message": f"Error executing code: {str(e)}"}