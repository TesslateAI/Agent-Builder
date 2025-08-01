# builder/backend/agents/flow_builder_agent.py
"""Flow Builder Agent for generating ReactFlow JSON."""

from tframex import TFrameXApp


def register_flow_builder_agent(app: TFrameXApp):
    """Register the Flow Builder agent."""
    
    flow_builder_agent_prompt = """You are a FlowBuilderAgent. Generate ReactFlow JSON that implements the flow instruction.

INSTRUCTION: {flow_instruction}

Available Components:
{available_components_context}

RULES:
1. Output ONLY valid JSON - no text, no explanations
2. Must have "nodes" and "edges" arrays
3. Use exact component IDs from available components list
4. Include ALL components mentioned in instruction

COMPONENT TYPES:
- AGENTS: type = agent ID, data = {{label, component_category: "agent", selected_tools: [], template_vars_config: {{}}}}
- TOOLS: type = tool ID, data = {{label, component_category: "tool"}}  
- PATTERNS: type = pattern name, data = {{label, component_category: "pattern", [required_params]}}

PATTERN PARAMS:
- DiscussionPattern: participants: [agent_ids]
- SequentialPattern: steps_config: [agent_ids]
- ParallelPattern: tasks: [agent_ids]
- RouterPattern: router_agent_name: string, routes: {{}}

Think step-by-step using <think>...</think> tags.
The final output MUST be ONLY the JSON object.
"""
    
    @app.agent(
        name="FlowBuilderAgent",
        description="Specialized agent that generates ReactFlow JSON based on instructions from the ConversationalAssistant.",
        system_prompt=flow_builder_agent_prompt,
        strip_think_tags=True
    )
    async def _flow_builder_agent_placeholder():
        pass