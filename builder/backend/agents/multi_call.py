# backend/agents/multi_call.py
import logging
import os
from tframex.systems import MultiCallSystem # Assuming tframex is importable

logger = logging.getLogger(__name__)

# Get output dir from env or use a default relative to backend/
DEFAULT_MULTI_CALL_OUTPUT_DIR = os.getenv("MULTI_CALL_OUTPUT_DIR", "example_outputs/ex4_multi_call_outputs")


async def execute_multi_call_system(system_instance: MultiCallSystem, input_data: dict) -> dict:
    """
    Executes the MultiCallSystem logic.
    Input data expected: {'prompt': str, 'num_calls': int, 'base_filename': str, 'max_tokens': Optional[int]}
                         (output_dir is part of system config, not runtime input)
    Output data: {'output': str} # Returns a summary string
    """
    prompt = input_data.get('prompt')
    num_calls = input_data.get('num_calls', 3) # Default if not provided
    base_filename = input_data.get('base_filename', 'multi_output')
    max_tokens = input_data.get('max_tokens')
    # Output dir comes from system config (env var)
    output_dir = system_instance.default_output_dir # Access the configured dir

    if not prompt:
        return {"output": "Error: 'prompt' input is missing."}

    logger.info(f"Running MultiCallSystem with prompt: '{prompt[:50]}...', num_calls: {num_calls}, base_filename: {base_filename}, output_dir: {output_dir}, max_tokens: {max_tokens}")

    try:
        # Ensure output dir exists before running
        os.makedirs(output_dir, exist_ok=True)

        results = await system_instance.run(
            prompt=prompt,
            num_calls=num_calls,
            output_dir=output_dir, # Pass the configured dir
            base_filename=base_filename,
            max_tokens=max_tokens
        )
        # Format results for display
        result_summary = f"MultiCallSystem completed. Results saved in '{output_dir}'.\nSummary:\n"
        for task_id, result_path_or_error in results.items():
                result_summary += f"  - {task_id}: {result_path_or_error}\n"
        return {"output": result_summary} # Return the summary string

    except Exception as e:
        logger.error(f"MultiCallSystem execution encountered an error: {e}", exc_info=True)
        return {"output": f"Error during execution: {e}"}