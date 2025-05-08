# backend/agents/chain.py
import logging
from tframex.systems import ChainOfAgents # Assuming tframex is importable

logger = logging.getLogger(__name__)

async def execute_chain_system(system_instance: ChainOfAgents, input_data: dict) -> dict:
    """
    Executes the ChainOfAgents system logic.
    Input data expected: {'initial_prompt': str, 'long_text': str, 'max_tokens': Optional[int]}
                         (chunk_size, chunk_overlap are part of system config, not runtime input)
    Output data: {'output': str}
    """
    initial_prompt = input_data.get('initial_prompt')
    long_text = input_data.get('long_text')
    max_tokens = input_data.get('max_tokens') # Can be None

    if not initial_prompt:
        return {"output": "Error: 'initial_prompt' input is missing."}
    if not long_text:
        return {"output": "Error: 'long_text' input is missing."}

    logger.info(f"Running ChainOfAgents with initial_prompt: '{initial_prompt[:50]}...', long_text: '{long_text[:50]}...', max_tokens: {max_tokens}")
    try:
        # Pass kwargs like max_tokens down
        response = await system_instance.run(
            initial_prompt=initial_prompt,
            long_text=long_text,
            max_tokens=max_tokens
        )
        return {"output": response}
    except Exception as e:
        logger.error(f"ChainOfAgents execution encountered an error: {e}", exc_info=True)
        return {"output": f"Error during execution: {e}"}