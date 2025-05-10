# builder/backend/agents/prompt_injector_agent.py
import logging
import re
import json
from typing import List, Dict, Tuple, Optional
from tframex.agents import BaseAgent # For type hinting and consistency
from .utils import strip_think_tags # To clean up potential <think> tags in pasted input

logger = logging.getLogger(__name__)

def _parse_manual_input(full_prompt: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Parses the full input prompt to extract memory and file prompts.
    Expected format:
    <memory>...</memory>
    <prompt filename="path/to/file1.html">...</prompt>
    <prompt filename="path/to/style.css">...</prompt>
    """
    memory_content = None
    prompts = []

    if not isinstance(full_prompt, str):
        logger.error("Full prompt is not a string.")
        return None, []

    # Extract memory
    memory_match = re.search(r"<memory>(.*?)</memory>", full_prompt, re.DOTALL | re.IGNORECASE)
    if memory_match:
        memory_content = memory_match.group(1).strip()
        logger.info("Extracted memory block from manual input.")
    else:
        logger.warning("Could not find <memory> block in manual input.")

    # Extract prompts - SIMPLIFIED REGEX, NO URL
    prompt_pattern = re.compile(
        r'<prompt\s+filename="(?P<filename>[^"]+)">(?P<prompt_content>.*?)</prompt>', # Removed url part
        re.DOTALL | re.IGNORECASE
    )
    
    for match in prompt_pattern.finditer(full_prompt):
        data = match.groupdict()
        filename = data['filename'].strip()
        prompt_content = data['prompt_content'].strip()

        if filename and prompt_content:
            prompts.append({
                "filename": filename,
                # "url": filename, # No longer using URL explicitly, FileGenerator will use filename for path
                "prompt": prompt_content
            })
            logger.debug(f"Extracted prompt for file: {filename} from manual input.")
        else:
            logger.warning(f"Found prompt block in manual input but filename or content was empty: {match.group(0)}")

    if not prompts and memory_content is not None:
         logger.warning("Extracted memory, but no valid <prompt ...> blocks found in manual input.")
    elif not prompts and memory_content is None:
         logger.warning("Could not find any <memory> or <prompt ...> blocks in manual input.")
    
    return memory_content, prompts

async def execute_prompt_injector_agent(agent_instance: BaseAgent, input_data: dict) -> dict:
    """
    Executes the Prompt Injector Agent logic.
    Input: {'full_prompt': str}
    Output: {'memory': Optional[str], 'file_prompts_json': str}
    """
    full_prompt_raw = input_data.get('full_prompt')

    if not full_prompt_raw:
        logger.error("PromptInjectorAgent execution failed: 'full_prompt' input is missing.")
        return {"memory": None, "file_prompts_json": "[]", "error": "Error: Full prompt input is missing."}

    full_prompt = strip_think_tags(full_prompt_raw)
    
    logger.info(f"Running PromptInjectorAgent with provided prompt (length: {len(full_prompt)}).")
    try:
        memory, file_prompts_list = _parse_manual_input(full_prompt)
        file_prompts_json = json.dumps(file_prompts_list)

        if memory is None and not file_prompts_list:
             logger.warning("PromptInjectorAgent: Parsed no memory and no file prompts from the input.")

        return {"memory": memory, "file_prompts_json": file_prompts_json}

    except Exception as e:
        logger.error(f"PromptInjectorAgent execution encountered an error: {e}", exc_info=True)
        return {"memory": None, "file_prompts_json": "[]", "error": f"Error during PromptInjectorAgent execution: {e}"}