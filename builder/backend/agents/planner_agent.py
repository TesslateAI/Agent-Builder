# Filename: builder/backend/agents/planner_agent.py

import logging
from tframex.agents import BaseAgent # Use BaseAgent for potential future state
from tframex.model import VLLMModel
from .utils import strip_think_tags # Import the shared utility

logger = logging.getLogger(__name__)

# Agent Configuration (Could be loaded from env or passed during init)
DEFAULT_MAX_TOKENS_PLAN = 34000
DEFAULT_TEMPERATURE = 0.5

async def execute_planner_agent(agent_instance: BaseAgent, input_data: dict) -> dict:
    """
    Executes the Planner Agent logic.
    Input: {'user_request': str}
    Output: {'plan': str}
    """
    user_request = input_data.get('user_request')
    max_tokens = input_data.get('max_tokens', DEFAULT_MAX_TOKENS_PLAN) # Allow override

    if not user_request:
        logger.error("PlannerAgent execution failed: 'user_request' input is missing.")
        return {"plan": "Error: User Request input is missing."}

    planner_prompt = f"""
You are an expert software architect and planner. Your goal is to create a comprehensive plan to build the software requested by the user.

User Request: "{user_request}"

Instructions:
1.  Analyze the user request thoroughly.
2.  Think through the project structure: Define a clear and logical directory and file structure. List all necessary files (HTML, CSS, JavaScript, images, etc.).
3.  Think through styling and UI/UX: Describe the desired look and feel, color palette, typography, and any key UI components. Consider responsiveness.
4.  Think through images and media: Identify the types of images or media needed and suggest placeholders or sources if applicable.
5.  Think through formatting and content: Outline the content required for each page or component.
6.  Think through frameworks and libraries: Recommend appropriate technologies (e.g., Tailwind CSS was mentioned in context, stick to basic HTML/CSS/JS if not specified, but plan for it if requested). If using libraries, specify how they should be included (CDN, local).
7.  Think through caveats and best practices: Mention any potential challenges, limitations, or important development practices (like accessibility, SEO basics for web).
8.  Output *only* the detailed plan in a clear, structured format (e.g., using markdown). Do not include any conversational text before or after the plan itself. Ensure the plan is detailed enough for another agent to break it down into specific file-generation tasks.
"""
    logger.info(f"Running PlannerAgent for request: '{user_request[:100]}...'")
    try:
        # Use the agent's underlying model call method
        # Note: BaseAgent doesn't directly have .run(), we use the model
        # If PlannerAgent inherited BaseAgent, we could use self._stream_and_aggregate
        # Assuming agent_instance provides access to the model or a run method
        raw_plan_response = await agent_instance.model.call_stream_and_aggregate(
             messages=[{"role": "user", "content": planner_prompt}],
             max_tokens=max_tokens,
             temperature=DEFAULT_TEMPERATURE
             # agent_instance might need a wrapper .run() like BasicAgent
             # For simplicity, assume agent_instance has a model reference and we call directly
             # or it's a BasicAgent instance as passed by constructor in agent_definitions
             # Let's assume it's a BasicAgent instance passed in.
             # raw_plan_response = await agent_instance.run(planner_prompt, max_tokens=max_tokens, temperature=DEFAULT_TEMPERATURE)
        )

        plan = strip_think_tags(raw_plan_response)

        if not plan or plan.startswith("ERROR:"):
             logger.error(f"Planner Agent failed or returned an error: {plan}")
             return {"plan": f"Error: Planner Agent failed. Details: {plan}"}

        logger.info("Planner Agent finished successfully.")
        # Save plan artifact (optional here, could be done by executor if needed)
        # save_file("plan.md", f"User Request:\n{user_request}\n\n---\n\nGenerated Plan:\n{plan}", base_dir="build_artifacts") # Requires run_id context to save properly per run

        return {"plan": plan}
    except Exception as e:
        logger.error(f"PlannerAgent execution encountered an error: {e}", exc_info=True)
        return {"plan": f"Error during PlannerAgent execution: {e}"}

# Helper specific to VLLMModel used in flow_executor's get_model()
# Add a stream aggregation helper if not using BasicAgent directly
async def _stream_and_aggregate_helper(model, messages, **kwargs):
    full_response = ""
    async for chunk in model.call_stream(messages, **kwargs):
        full_response += chunk
    return full_response

# Add the helper to VLLMModel if it doesn't exist or use BasicAgent
VLLMModel.call_stream_and_aggregate = _stream_and_aggregate_helper