# builder/backend/utils.py
import logging
import re
from typing import Optional, Dict, Any # Added for find_logical_name

logger = logging.getLogger(__name__) # Use utils logger

def strip_think_tags(text: str) -> str:
    """Removes content up to and including the first </think> tag if present."""
    if not isinstance(text, str): # Ensure input is a string
        return text # Return non-strings as-is

    think_end_tag = "</think>"
    tag_pos = text.find(think_end_tag)
    if tag_pos != -1:
        # Removed debug logging for cleaner output, can be added back if needed
        # logger.debug("Found </think> tag, stripping preceding content.")
        content_after = text[tag_pos + len(think_end_tag):].strip()
        return content_after
    else:
        # logger.debug("No </think> tag found, using full response.")
        return text.strip() # Return original text (stripped) if tag not found

# Optional: Move find_logical_name_for_handle here too, as it's also utility-like
# and helps keep flow_executor focused on execution.
def find_logical_name_for_handle(definition: Dict, handle_id: str, io_type: str) -> Optional[str]:
    """Finds the logical input/output name corresponding to a handle ID."""
    if not definition or io_type not in definition:
        return None
    io_map = definition[io_type] # Either 'inputs' or 'outputs' dict
    for logical_name, details in io_map.items():
        # Ensure details is a dictionary before accessing .get()
        if isinstance(details, dict) and details.get('handle_id') == handle_id:
            return logical_name
    # Fallback: if handle_id itself is a key (less likely with new structure)
    if handle_id in io_map:
        # logger.debug(f"Falling back to using handle_id '{handle_id}' as logical name for {io_type}.")
        return handle_id
    return None