# builder/backend/builtin_tools/utilities.py
"""
Utility tools for the Agent-Builder application.
Provides date/time operations and mathematical calculations.
"""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List


def register_utility_tools(tframex_app):
    """Register utility tools with the TFrameXApp instance."""
    
    @tframex_app.tool(
        name="Date & Time Tool",
        description="Work with dates and times including formatting, parsing, and calculations"
    )
    async def datetime_tool(
        operation: str,
        date_string: str = None,
        format_string: str = "%Y-%m-%d %H:%M:%S",
        timezone: str = "UTC",
        days_offset: int = 0
    ) -> Dict[str, Any]:
        """Perform datetime operations."""
        try:
            result = {"success": True, "operation": operation}
            
            if operation == "now":
                now = datetime.now()
                result["datetime"] = now.strftime(format_string)
                result["timestamp"] = now.timestamp()
                result["iso"] = now.isoformat()
            
            elif operation == "parse" and date_string:
                dt = datetime.strptime(date_string, format_string)
                result["datetime"] = dt
                result["timestamp"] = dt.timestamp()
                result["iso"] = dt.isoformat()
            
            elif operation == "format" and date_string:
                # Try to parse common formats first
                dt = None
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        dt = datetime.strptime(date_string, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt:
                    result["formatted"] = dt.strftime(format_string)
                else:
                    result["success"] = False
                    result["error"] = "Could not parse date string"
            
            elif operation == "add_days":
                if date_string:
                    dt = datetime.strptime(date_string, format_string)
                else:
                    dt = datetime.now()
                
                new_dt = dt + timedelta(days=days_offset)
                result["original"] = dt.strftime(format_string)
                result["new_datetime"] = new_dt.strftime(format_string)
                result["days_added"] = days_offset
            
            else:
                result["success"] = False
                result["error"] = f"Unknown operation: {operation}"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"DateTime error: {str(e)}"
            }
    
    @tframex_app.tool(
        name="Math Calculator",
        description="Perform mathematical calculations including basic arithmetic, statistics, and functions"
    )
    async def math_calculator(
        operation: str,
        numbers: List[float] = None,
        expression: str = None
    ) -> Dict[str, Any]:
        """Perform mathematical operations."""
        try:
            result = {"success": True, "operation": operation}
            
            if operation == "eval" and expression:
                # Safe evaluation of mathematical expressions
                allowed_names = {
                    k: v for k, v in math.__dict__.items()
                    if not k.startswith("__")
                }
                allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
                
                try:
                    value = eval(expression, {"__builtins__": {}}, allowed_names)
                    result["value"] = value
                    result["expression"] = expression
                except Exception as e:
                    result["success"] = False
                    result["error"] = f"Expression evaluation error: {str(e)}"
            
            elif numbers:
                if operation == "sum":
                    result["value"] = sum(numbers)
                elif operation == "mean":
                    result["value"] = sum(numbers) / len(numbers)
                elif operation == "median":
                    sorted_nums = sorted(numbers)
                    n = len(sorted_nums)
                    if n % 2 == 0:
                        result["value"] = (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
                    else:
                        result["value"] = sorted_nums[n//2]
                elif operation == "min":
                    result["value"] = min(numbers)
                elif operation == "max":
                    result["value"] = max(numbers)
                elif operation == "std":
                    mean = sum(numbers) / len(numbers)
                    variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
                    result["value"] = math.sqrt(variance)
                else:
                    result["success"] = False
                    result["error"] = f"Unknown operation for numbers: {operation}"
                
                if result.get("value") is not None:
                    result["count"] = len(numbers)
                    result["numbers"] = numbers
            
            else:
                result["success"] = False
                result["error"] = "No numbers or expression provided"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Math calculation error: {str(e)}"
            }
    
    return 2  # Number of tools registered