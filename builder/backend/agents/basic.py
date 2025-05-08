# backend/agents/basic.py
import logging
from tframex.agents import BasicAgent # Assuming tframex is importable

logger = logging.getLogger(__name__)

async def execute_basic_agent(agent_instance: BasicAgent, input_data: dict) -> dict:
    """
    Executes the BasicAgent logic.
    Input data expected: {'prompt': str, 'max_tokens': Optional[int]}
    Output data: {'output': str}
    """
    prompt = input_data.get('prompt')
    max_tokens = input_data.get('max_tokens') # Can be None

    if not prompt:
        logger.error("BasicAgent execution failed: 'prompt' input is missing.")
        # You might want to raise an exception or return an error structure
        return {"output": "Error: Prompt input is missing."}

    logger.info(f"Running BasicAgent with prompt: '{prompt[:50]}...', max_tokens: {max_tokens}")
    try:
        response = await agent_instance.run(prompt=prompt, max_tokens=max_tokens)
        return {"output": response}
    except Exception as e:
        logger.error(f"BasicAgent execution encountered an error: {e}", exc_info=True)
        return {"output": f"Error during execution: {e}"}