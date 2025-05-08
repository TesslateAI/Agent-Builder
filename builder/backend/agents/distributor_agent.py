# Filename: builder/backend/agents/distributor_agent.py

import logging
import re
import json
from typing import List, Dict, Tuple, Optional
from tframex.agents import BaseAgent # Use BaseAgent
from .utils import strip_think_tags # Import the shared utility

logger = logging.getLogger(__name__)

# Agent Configuration
DEFAULT_MAX_TOKENS_PLAN = 34000
DEFAULT_TEMPERATURE = 0.5

# --- Helper Function (Moved from original script) ---
def _parse_task_distribution(dist_output: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Parses the Task Distributor output to extract memory and file prompts.
    Expected format:
    <memory>...</memory>
    <prompt filename="file1.html" url="...">...</prompt>
    <prompt filename="style.css" url="...">...</prompt>
    """
    memory = None
    prompts = []

    # Extract memory
    memory_match = re.search(r"<memory>(.*?)</memory>", dist_output, re.DOTALL | re.IGNORECASE)
    if memory_match:
        memory = memory_match.group(1).strip()
        logger.info("Extracted memory block.")
    else:
        logger.warning("Could not find <memory> block in Task Distributor output.")

    # Extract prompts
    prompt_pattern = re.compile(
        r'<prompt\s+filename="(?P<filename>[^"]+)"(?:\s+url="(?P<url>[^"]+)?"\s*)?>(?P<prompt_content>.*?)</prompt>',
        re.DOTALL | re.IGNORECASE
    )
    for match in prompt_pattern.finditer(dist_output):
        data = match.groupdict()
        filename = data['filename'].strip()
        prompt_content = data['prompt_content'].strip()
        url = data.get('url', '').strip() # Handle optional url

        if filename and prompt_content:
            prompts.append({
                "filename": filename,
                "url": url if url else filename, # Default url to filename if not provided
                "prompt": prompt_content
            })
            logger.debug(f"Extracted prompt for file: {filename}")
        else:
            logger.warning(f"Found prompt block but filename or content was empty: {match.group(0)}")

    if not prompts:
         logger.warning("Could not find any valid <prompt ...> blocks in Task Distributor output.")

    return memory, prompts
# --- End Helper Function ---


async def execute_distributor_agent(agent_instance: BaseAgent, input_data: dict) -> dict:
    """
    Executes the Task Distributor Agent logic.
    Input: {'plan': str}
    Output: {'memory': str, 'file_prompts_json': str} # Pass prompts as JSON string
    """
    plan = input_data.get('plan')
    max_tokens = input_data.get('max_tokens', DEFAULT_MAX_TOKENS_PLAN)

    if not plan:
        logger.error("DistributorAgent execution failed: 'plan' input is missing.")
        return {"memory": None, "file_prompts_json": "[]", "error": "Error: Plan input is missing."} # Return error in output dict too

    distributor_prompt = f"""
You are a task distribution agent. Your input is a software development plan. Your goal is to break down this plan into:
1.  A shared `<memory>` block containing essential context, design guidelines, framework choices, and overall architecture described in the plan that *all* subsequent file-generation agents need to know to ensure consistency. This should be lengthy.
2.  Individual `<prompt>` blocks, one for *each file* identified in the plan's file structure. Each prompt block must specify the target `filename` and contain a highly detailed and specific prompt instructing another agent on *exactly* what code to generate for that single file, referencing the shared memory/plan as needed.
Any information the prompt that is coupled with another file, the entire integration must be properly and fully explained. Make the most solid pseudocode possible and talk about every single tiny detail in the prompt.
Development Plan:
--- START PLAN ---
{plan}
--- END PLAN ---

Instructions:
1.  Carefully read the entire Development Plan.
2.  Extract the core principles, design language, chosen frameworks/libraries, color schemes, typography, file structure overview, and any global requirements into a concise `<memory>` block. This memory block should *not* contain specific file contents but rather the shared context.
3.  For *each* file mentioned in the plan's file structure (e.g., index.html, style.css, script.js, about.html, assets/logo.png):
    *   If it's a code file (HTML, CSS, JS, etc.): Create a `<prompt filename="path/to/file.ext">` block. Inside this block, write a very specific prompt detailing exactly what code needs to be in this file. Include details about structure, content (referencing the plan), functionality, required HTML elements, CSS classes (mentioning framework if used), JS functions, links to other files (using relative paths based on the plan's structure), and references to the shared `<memory>` context if necessary. Instruct the agent receiving this prompt to output *only* the raw code for the file, enclosed in appropriate markdown ``` code blocks.
    *   If it's a non-code asset (like an image placeholder path mentioned in the plan): You can optionally create a prompt block instructing to note this placeholder or skip creating a prompt block for it. Focus on generating code files.
4.  Ensure filenames and relative paths in the prompts are consistent with the file structure defined in the plan.
5.  Output *only* the `<memory>` block followed immediately by all the `<prompt>` blocks. Do not include any other conversational text, introductions, or summaries.

Example Output Structure:
<memory>
Shared context, design guidelines, framework info...
</memory>
<prompt filename="index.html" url="index.html">
Generate the complete HTML structure for the main landing page (index.html). Use semantic HTML5 tags. Include a header, navigation (linking to about.html), main content area, and footer based on the plan and shared memory design. Use Tailwind CSS classes defined in the memory block for styling. Content should be based on the 'Home Page Content' section of the plan. Output only the complete HTML code in a ```html ... ``` block.
</prompt>
<prompt filename="css/style.css" url="css/style.css">
Generate the CSS rules for the website based on the plan and memory. Define styles for base elements, utility classes (if not using a framework like Tailwind mentioned in memory), and specific component styles outlined in the plan. Reference the color palette and typography from memory. Output only the CSS code in a ```css ... ``` block.
</prompt>
<prompt filename="js/script.js" url="js/script.js">
Generate the JavaScript code for interactive elements mentioned in the plan, like a mobile menu toggle or an image carousel. Ensure code is clean and follows best practices mentioned in memory. Output only the JavaScript code in a ```javascript ... ``` block.
</prompt>
... (more prompt blocks for other files)
"""

    logger.info(f"Running DistributorAgent...")
    try:
        # Use BasicAgent instance passed in
        raw_dist_response = await agent_instance.run(distributor_prompt, max_tokens=max_tokens, temperature=DEFAULT_TEMPERATURE)
        dist_output = strip_think_tags(raw_dist_response)

        if not dist_output or dist_output.startswith("ERROR:"):
            logger.error(f"Task Distributor Agent failed or returned an error: {dist_output}")
            return {"memory": None, "file_prompts_json": "[]", "error": f"Error: Distributor Agent failed. Details: {dist_output}"}

        logger.info("Task Distributor Agent finished. Parsing output...")
        memory, file_prompts = _parse_task_distribution(dist_output)

        if not memory or not file_prompts:
            logger.error("Failed to parse memory or file prompts from Task Distributor output.")
            # Save raw output artifact (optional here)
            # save_file("task_distribution_raw_output.txt", ..., base_dir="build_artifacts")
            return {"memory": memory, "file_prompts_json": "[]", "error": "Error: Failed to parse Task Distributor output. Check logs."}

        logger.info(f"Successfully parsed memory and {len(file_prompts)} file prompts.")
        # Save parsed data artifact (optional here)
        # parsed_prompts_log = f"<memory>\n{memory}\n</memory>\n\n" + ...
        # save_file("task_distribution_parsed.txt", parsed_prompts_log, base_dir="build_artifacts")

        # Serialize file_prompts to JSON string for output
        file_prompts_json = json.dumps(file_prompts)

        return {"memory": memory, "file_prompts_json": file_prompts_json}

    except Exception as e:
        logger.error(f"DistributorAgent execution encountered an error: {e}", exc_info=True)
        return {"memory": None, "file_prompts_json": "[]", "error": f"Error during DistributorAgent execution: {e}"}