# builder/backend/builtin_tools/text_processing.py
"""
Text processing tools for the Agent-Builder application.
Provides regex operations and text transformations.
"""

import re
from typing import Any, Dict


def register_text_processing_tools(tframex_app):
    """Register text processing tools with the TFrameXApp instance."""
    
    @tframex_app.tool(
        name="Text Pattern Matcher",
        description="Perform regex operations on text including search, replace, and extraction"
    )
    async def text_regex(
        text: str,
        pattern: str,
        operation: str = "search",
        replacement: str = "",
        flags: str = ""
    ) -> Dict[str, Any]:
        """Perform regex operations on text."""
        try:
            # Parse flags
            regex_flags = 0
            if 'i' in flags.lower():
                regex_flags |= re.IGNORECASE
            if 'm' in flags.lower():
                regex_flags |= re.MULTILINE
            if 's' in flags.lower():
                regex_flags |= re.DOTALL
            
            compiled_pattern = re.compile(pattern, regex_flags)
            
            result = {"success": True, "operation": operation, "pattern": pattern}
            
            if operation == "search":
                matches = compiled_pattern.findall(text)
                result["matches"] = matches
                result["count"] = len(matches)
            
            elif operation == "replace":
                new_text = compiled_pattern.sub(replacement, text)
                result["text"] = new_text
                result["replacements"] = len(compiled_pattern.findall(text))
            
            elif operation == "split":
                parts = compiled_pattern.split(text)
                result["parts"] = parts
                result["count"] = len(parts)
            
            elif operation == "match":
                match = compiled_pattern.match(text)
                if match:
                    result["match"] = match.group(0)
                    result["groups"] = match.groups()
                else:
                    result["match"] = None
            
            else:
                result["success"] = False
                result["error"] = f"Unknown operation: {operation}"
            
            return result
            
        except re.error as e:
            return {
                "success": False,
                "error": f"Regex error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Text processing error: {str(e)}"
            }
    
    @tframex_app.tool(
        name="Text Transformer",
        description="Transform text with various operations like case changes, formatting, and cleaning"
    )
    async def text_transform(
        text: str,
        operation: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Transform text with various operations."""
        try:
            options = options or {}
            result = {"success": True, "operation": operation, "original_length": len(text)}
            
            if operation == "upper":
                result["text"] = text.upper()
            elif operation == "lower":
                result["text"] = text.lower()
            elif operation == "title":
                result["text"] = text.title()
            elif operation == "capitalize":
                result["text"] = text.capitalize()
            elif operation == "strip":
                chars = options.get("chars")
                result["text"] = text.strip(chars)
            elif operation == "replace":
                old = options.get("old", "")
                new = options.get("new", "")
                result["text"] = text.replace(old, new)
            elif operation == "truncate":
                max_length = options.get("max_length", 100)
                suffix = options.get("suffix", "...")
                if len(text) > max_length:
                    result["text"] = text[:max_length - len(suffix)] + suffix
                else:
                    result["text"] = text
            elif operation == "word_count":
                words = text.split()
                result["word_count"] = len(words)
                result["char_count"] = len(text)
                result["line_count"] = len(text.splitlines())
            elif operation == "extract_emails":
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, text)
                result["emails"] = emails
                result["count"] = len(emails)
            elif operation == "extract_urls":
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                urls = re.findall(url_pattern, text)
                result["urls"] = urls
                result["count"] = len(urls)
            else:
                result["success"] = False
                result["error"] = f"Unknown operation: {operation}"
            
            if "text" in result:
                result["new_length"] = len(result["text"])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Text transformation error: {str(e)}"
            }
    
    return 2  # Number of tools registered