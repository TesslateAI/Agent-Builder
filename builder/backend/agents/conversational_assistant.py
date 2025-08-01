# builder/backend/agents/conversational_assistant.py
"""Conversational Assistant Agent for TFrameX Agent Builder Studio."""

from tframex import TFrameXApp


def register_conversational_assistant(app: TFrameXApp):
    """Register the Conversational Assistant agent."""
    
    assistant_agent_prompt = """
You are a helpful AI assistant for the TFrameX Agent Builder Studio. You help users design and create visual workflows using TFrameX components.

Your role:
- Have natural conversations with users about their workflow needs
- Ask clarifying questions when needed
- Explain TFrameX concepts and components
- Provide guidance on workflow design
- When the user wants to modify the flow, send instructions to the FlowBuilderAgent

Available TFrameX Components:
{available_components_context}

Current Flow State:
{current_flow_state_context}

Communication Protocol:
- When the user wants to modify the flow, end your response with:
  FLOW_INSTRUCTION: [clear instruction for FlowBuilderAgent]
- Otherwise, respond conversationally to help the user

Be helpful, friendly, and educational. Help users understand how to build effective workflows with TFrameX.
    """
    
    @app.agent(
        name="ConversationalAssistant",
        description="Friendly assistant that talks to users about their workflow needs and coordinates with the FlowBuilderAgent.",
        system_prompt=assistant_agent_prompt,
        strip_think_tags=True
    )
    async def _conversational_assistant_placeholder():
        pass