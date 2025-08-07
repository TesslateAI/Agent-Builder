# builder/backend/agents/__init__.py
"""Agent registration module for TFrameX Agent Builder."""

from .conversational_assistant import register_conversational_assistant
from .flow_builder_agent import register_flow_builder_agent
from .orchestrator_agent import register_orchestrator_agent
from .research_agent import register_research_agent
from .content_generator import register_content_generator_agent
from .data_transform import register_data_transform_agent
from .validation_agent import register_validation_agent
from .file_processor import register_file_processor_agent

__all__ = [
    'register_conversational_assistant',
    'register_flow_builder_agent', 
    'register_orchestrator_agent',
    'register_research_agent',
    'register_content_generator_agent',
    'register_data_transform_agent',
    'register_validation_agent',
    'register_file_processor_agent'
]