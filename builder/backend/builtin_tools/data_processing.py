# builder/backend/builtin_tools/data_processing.py
"""
Data processing tools for the Agent-Builder application.
Provides JSON and CSV data manipulation capabilities.
"""

import io
import json
import logging
import os
from typing import Any, Dict, List, Union

# Optional imports - tools will be disabled if dependencies are missing
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger(__name__)


def register_data_processing_tools(tframex_app):
    """Register data processing tools with the TFrameXApp instance."""
    tools_registered = 0
    
    @tframex_app.tool(
        name="json_processor",
        description="Parse, manipulate, and query JSON data with JSONPath-like operations"
    )
    async def process_json(
        json_data: Union[str, Dict, List],
        operation: str = "parse",
        path: str = None,
        new_value: Any = None
    ) -> Dict[str, Any]:
        """Process JSON data with various operations."""
        try:
            # Parse JSON if string
            if isinstance(json_data, str):
                try:
                    data = json.loads(json_data)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Invalid JSON: {str(e)}"
                    }
            else:
                data = json_data
            
            result = {"success": True, "operation": operation}
            
            if operation == "parse":
                result["data"] = data
                result["type"] = type(data).__name__
                if isinstance(data, dict):
                    result["keys"] = list(data.keys())
                elif isinstance(data, list):
                    result["length"] = len(data)
            
            elif operation == "get" and path:
                # Simple path navigation (e.g., "user.name" or "items[0].title")
                try:
                    current = data
                    for part in path.replace('[', '.').replace(']', '').split('.'):
                        if part.isdigit():
                            current = current[int(part)]
                        else:
                            current = current[part]
                    result["value"] = current
                except (KeyError, IndexError, TypeError) as e:
                    result["success"] = False
                    result["error"] = f"Path not found: {path}"
            
            elif operation == "keys" and isinstance(data, dict):
                result["keys"] = list(data.keys())
            
            elif operation == "values" and isinstance(data, dict):
                result["values"] = list(data.values())
            
            elif operation == "length":
                if hasattr(data, '__len__'):
                    result["length"] = len(data)
                else:
                    result["error"] = "Data type does not support length"
            
            elif operation == "pretty":
                result["formatted"] = json.dumps(data, indent=2, ensure_ascii=False)
            
            else:
                result["error"] = f"Unknown operation: {operation}"
                result["success"] = False
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"JSON processing error: {str(e)}"
            }
    
    tools_registered += 1
    
    # CSV processing tool (requires pandas)
    if HAS_PANDAS:
        @tframex_app.tool(
            name="csv_data_processor",
            description="Read, write, and manipulate CSV data with pandas-like operations"
        )
        async def process_csv(
            csv_data: str = None,
            file_path: str = None,
            operation: str = "read",
            delimiter: str = ",",
            headers: List[str] = None
        ) -> Dict[str, Any]:
            """Process CSV data with various operations."""
            try:
                if operation == "read":
                    if csv_data:
                        df = pd.read_csv(io.StringIO(csv_data), delimiter=delimiter)
                    elif file_path and os.path.exists(file_path):
                        df = pd.read_csv(file_path, delimiter=delimiter)
                    else:
                        return {
                            "success": False,
                            "error": "No CSV data or valid file path provided"
                        }
                    
                    return {
                        "success": True,
                        "data": df.to_dict('records'),
                        "columns": df.columns.tolist(),
                        "shape": df.shape,
                        "info": {
                            "rows": len(df),
                            "columns": len(df.columns),
                            "dtypes": df.dtypes.to_dict()
                        }
                    }
                
                elif operation == "summary" and csv_data:
                    df = pd.read_csv(io.StringIO(csv_data), delimiter=delimiter)
                    return {
                        "success": True,
                        "summary": df.describe().to_dict(),
                        "null_counts": df.isnull().sum().to_dict(),
                        "data_types": df.dtypes.to_dict()
                    }
                
                else:
                    return {
                        "success": False,
                        "error": f"Unknown operation: {operation}"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"CSV processing error: {str(e)}"
                }
        
        tools_registered += 1
    else:
        logger.warning("pandas not available - CSV processing tool will be disabled")
    
    return tools_registered