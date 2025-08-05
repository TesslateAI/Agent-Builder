# builder/backend/builtin_tools/__init__.py
"""
Built-in tools module for the Agent-Builder application.
This module provides a centralized way to register all built-in tools with TFrameX.
"""

import logging

# Import all tool registration functions
from .code_execution import register_code_execution_tools
from .web_tools import register_web_tools
from .data_processing import register_data_processing_tools
from .text_processing import register_text_processing_tools
from .file_system import register_file_system_tools
from .utilities import register_utility_tools
from .flow_analysis import register_flow_analysis_tools

logger = logging.getLogger(__name__)


def register_builtin_tools(tframex_app):
    """Register all built-in tools with the TFrameXApp instance."""
    tools_registered = 0
    
    # Register all tool categories
    tool_categories = [
        ("Code Execution", register_code_execution_tools),
        ("Web Tools", register_web_tools),
        ("Data Processing", register_data_processing_tools),
        ("Text Processing", register_text_processing_tools),
        ("File System", register_file_system_tools),
        ("Utilities", register_utility_tools),
        ("Flow Analysis", register_flow_analysis_tools)
    ]
    
    for category_name, register_func in tool_categories:
        try:
            count = register_func(tframex_app)
            tools_registered += count
            logger.info(f"Registered {count} {category_name} tools")
        except Exception as e:
            logger.error(f"Failed to register {category_name} tools: {e}")
    
    # Check for missing dependencies and log warnings
    import importlib.util
    
    missing_deps = []
    if importlib.util.find_spec("aiohttp") is None:
        missing_deps.append("aiohttp (web tools may be limited)")
    
    if importlib.util.find_spec("pandas") is None:
        missing_deps.append("pandas (CSV processing disabled)")
    
    if importlib.util.find_spec("bs4") is None:
        missing_deps.append("beautifulsoup4 (web scraping disabled)")
    
    if missing_deps:
        logger.warning(f"Some built-in tools disabled due to missing dependencies: {', '.join(missing_deps)}")
    
    logger.info(f"Successfully registered {tools_registered} built-in tools")
    return tools_registered


# Export the main registration function
__all__ = ['register_builtin_tools']