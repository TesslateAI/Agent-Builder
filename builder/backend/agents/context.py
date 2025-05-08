# backend/agents/context.py
import logging
from tframex.agents import ContextAgent # Assuming tframex is importable

logger = logging.getLogger(__name__)

async def execute_context_agent(agent_instance: ContextAgent, input_data: dict) -> dict:
    """
    Executes the ContextAgent logic.
    Input data expected: {'prompt': str, 'context': str, 'max_tokens': Optional[int]}
    Output data: {'output': str}
    """
    prompt = input_data.get('prompt')
    context = input_data.get('context', '') # Default to empty string if missing
    max_tokens = input_data.get('max_tokens') # Can be None

    if not prompt:
        logger.error("ContextAgent execution failed: 'prompt' input is missing.")
        return {"output": "Error: Prompt input is missing."}

    # Update the agent's context dynamically IF context is provided in input_data
    # Otherwise, it uses the context it was initialized with (if any, though unlikely here)
    # A better approach might be to *always* expect context via input_data for stateless execution
    if 'context' in input_data:
         agent_instance.context = context # Update context before running

    logger.info(f"Running ContextAgent with prompt: '{prompt[:50]}...', context: '{context[:50]}...', max_tokens: {max_tokens}")
    try:
        response = await agent_instance.run(prompt=prompt, max_tokens=max_tokens)
        return {"output": response}
    except Exception as e:
        logger.error(f"ContextAgent execution encountered an error: {e}", exc_info=True)
        return {"output": f"Error during execution: {e}"}