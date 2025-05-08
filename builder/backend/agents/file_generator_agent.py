# Filename: builder/backend/agents/file_generator_agent.py

import logging
import re
import json
import os
import asyncio
import time
from typing import List, Dict, Optional, Any, Tuple
from tframex.agents import BaseAgent # Use BaseAgent
from .utils import strip_think_tags # Import the shared utility

logger = logging.getLogger(__name__)

# Agent Configuration
DEFAULT_MAX_TOKENS_FILE_GEN = 34000
DEFAULT_TEMPERATURE = 0.5
GENERATED_BASE_DIR = "generated" # Base directory for all runs

# --- Helper Functions (Moved/Adapted from original script) ---

def _extract_code(llm_output: str) -> Optional[str]:
    """Extracts the first code block (```...```) from LLM output."""
    # Regex to find markdown code blocks, capturing the content
    # It handles optional language identifiers (like ```html)
    match = re.search(r"```(?:[a-zA-Z0-9]*\n)?(.*?)```", llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        # Basic check if code seems plausible (not empty)
        if code:
            logger.debug(f"Extracted code block (length: {len(code)}).")
            return code
        else:
             logger.warning("Found code block delimiters but content inside was empty.")
             return None # Explicitly return None if block is empty
    else:
        logger.warning("No markdown code block found in the LLM output.")
        # Sometimes the LLM might forget the ```, attempt to return the whole thing if it looks like code
        if llm_output.strip().startswith('<') or llm_output.strip().startswith(('function', 'const', 'let', 'var', 'import', 'public class', '@', '.', '#')):
             logger.warning("No code block found, but output resembles code. Returning full output.")
             return llm_output.strip()
        return None

def _save_file(run_id: str, filename: str, content: str) -> Tuple[bool, str]:
    """Saves content to a file within the specific run's generated folder."""
    if not run_id:
        logger.error("Cannot save file: run_id is missing.")
        return False, ""

    # Construct path relative to the base generated directory
    run_dir = os.path.join(GENERATED_BASE_DIR, run_id)
    # Ensure the path is relative to the run directory (prevent traversal)
    # Basic security check
    if os.path.isabs(filename) or ".." in filename:
        logger.error(f"Invalid filename detected (absolute or traversal): {filename}")
        return False, ""

    full_path = os.path.join(run_dir, filename)
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully saved file: {full_path}")
        return True, full_path
    except OSError as e:
        logger.error(f"Failed to save file {full_path}: {e}")
        return False, full_path
    except Exception as e:
        logger.error(f"An unexpected error occurred saving file {full_path}: {e}")
        return False, full_path
# --- End Helper Functions ---

async def _generate_single_file(agent_instance: BaseAgent, run_id: str, filename: str, memory: str, specific_prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Internal task to generate and save a single file."""
    generation_prompt = f"""
<memory>
{memory}
</memory>

<prompt filename="{filename}">
{specific_prompt}
</prompt>

Based *only* on the specific prompt for `{filename}` above and the shared `<memory>` context, generate the complete, raw code content for the file `{filename}`.
Output *only* the raw code content for the file, enclosed in the appropriate markdown code block (e.g., ```html ... ```, ```css ... ```, ```javascript ... ```).
Do not include any other text, explanations, introductions, or summaries outside the code block.
For tailwind, use this: <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
"""
    file_result = {"filename": filename, "status": "failed", "path": None, "error": None}
    try:
        logger.debug(f"Starting generation task for: {filename} (Run ID: {run_id})")
        # Use BasicAgent instance passed in
        raw_response = await agent_instance.run(generation_prompt, max_tokens=max_tokens, temperature=temperature)
        generation_output = strip_think_tags(raw_response)

        if generation_output.startswith("ERROR:"):
             logger.error(f"Generation task for {filename} returned an error: {generation_output}")
             file_result["error"] = f"LLM Error: {generation_output}"
             _save_file(run_id, f"{filename}.error.txt", generation_output)
             return file_result

        code_content = _extract_code(generation_output)
        if code_content:
            saved_ok, saved_path = _save_file(run_id, filename, code_content)
            if saved_ok:
                file_result["status"] = "success"
                file_result["path"] = saved_path
            else:
                file_result["error"] = f"Failed to save file to {saved_path}"
        else:
            logger.error(f"Failed to extract code block for {filename}. Saving raw output.")
            file_result["error"] = "Failed to extract code block from LLM output."
            _save_file(run_id, f"{filename}.raw_output.txt", generation_output)

        return file_result

    except Exception as e:
        logger.error(f"Generation task for {filename} failed with exception: {e}", exc_info=True)
        file_result["error"] = f"Exception: {e}"
        _save_file(run_id, f"{filename}.error.txt", f"Task failed with exception:\n{e}")
        return file_result


async def execute_file_generator_agent(agent_instance: BaseAgent, input_data: dict) -> dict:
    """
    Executes the File Generator Agent logic.
    Input: {'memory': str, 'file_prompts_json': str, 'run_id': str}
    Output: {'generation_summary': str, 'preview_link': Optional[str]}
    """
    memory = input_data.get('memory')
    file_prompts_json = input_data.get('file_prompts_json')
    run_id = input_data.get('run_id') # Crucial input from executor
    max_tokens = input_data.get('max_tokens', DEFAULT_MAX_TOKENS_FILE_GEN)
    temperature = input_data.get('temperature', DEFAULT_TEMPERATURE)

    if not memory or not file_prompts_json or not run_id:
        error_msg = f"FileGeneratorAgent execution failed: Missing input. Got memory: {bool(memory)}, prompts: {bool(file_prompts_json)}, run_id: {bool(run_id)}"
        logger.error(error_msg)
        return {"generation_summary": error_msg, "preview_link": None}

    try:
        file_prompts: List[Dict[str, str]] = json.loads(file_prompts_json)
    except json.JSONDecodeError as e:
        error_msg = f"FileGeneratorAgent failed: Could not decode file_prompts_json: {e}"
        logger.error(error_msg)
        return {"generation_summary": error_msg, "preview_link": None}

    if not file_prompts:
        logger.warning("No file prompts provided to FileGeneratorAgent. Nothing to generate.")
        return {"generation_summary": "No files requested for generation.", "preview_link": None}

    # --- Parallel Execution ---
    logger.info(f"Running FileGeneratorAgent: Preparing {len(file_prompts)} file generation tasks for Run ID: {run_id}...")
    tasks = []
    for task_info in file_prompts:
        filename = task_info["filename"]
        specific_prompt = task_info["prompt"]

        task = _generate_single_file(
            agent_instance=agent_instance,
            run_id=run_id,
            filename=filename,
            memory=memory,
            specific_prompt=specific_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        tasks.append(task)

    logger.info(f"Launching {len(tasks)} file generation tasks concurrently...")
    start_time_gen = time.time()
    # results will be a list of dictionaries like file_result defined in _generate_single_file
    results: List[Dict[str, Any]] = await asyncio.gather(*tasks, return_exceptions=False) # Handle exceptions within task
    end_time_gen = time.time()
    logger.info(f"File generation tasks completed in {end_time_gen - start_time_gen:.2f} seconds.")

    # --- Process Results and Create Summary ---
    files_saved = 0
    files_failed = 0
    summary_lines = [f"File Generation Summary (Run ID: {run_id}):"]
    preview_target_file = None # Find index.html or similar for preview link

    for result in results:
        filename = result.get("filename", "Unknown File")
        status = result.get("status", "failed")
        path = result.get("path")
        error = result.get("error")

        if status == "success" and path:
            files_saved += 1
            summary_lines.append(f"  - [SUCCESS] {filename} -> {path}")
            # Check if this is a potential preview target
            if filename.lower() == 'index.html' or filename.lower().endswith('.html'):
                 if preview_target_file is None or filename.lower() == 'index.html': # Prioritize index.html
                     preview_target_file = filename
        else:
            files_failed += 1
            summary_lines.append(f"  - [FAILED]  {filename} - Error: {error}")

    summary_lines.append(f"\nFinished. Saved: {files_saved}, Failed/Skipped: {files_failed}")
    generation_summary = "\n".join(summary_lines)
    logger.info(f"File generation summary created for Run ID: {run_id}. Saved: {files_saved}, Failed: {files_failed}")

    # --- Generate Preview Link ---
    preview_link = None
    if preview_target_file:
        # Construct the relative URL path for the preview endpoint
        # Flask route will be /api/preview/<run_id>/<filepath>
        preview_link = f"/api/preview/{run_id}/{preview_target_file}"
        logger.info(f"Generated preview link: {preview_link}")

    return {"generation_summary": generation_summary, "preview_link": preview_link}