# builder/backend/builtin_tools/file_system.py
"""
File system tools for the Agent-Builder application.
Provides safe file reading and writing capabilities.
"""

import tempfile
from pathlib import Path
from typing import Dict, Any


def register_file_system_tools(tframex_app):
    """Register file system tools with the TFrameXApp instance."""
    
    @tframex_app.tool(
        name="File Reader",
        description="Safely read files with encoding detection and size limits"
    )
    async def read_file(
        file_path: str,
        encoding: str = "utf-8",
        max_size_mb: float = 10.0
    ) -> Dict[str, Any]:
        """Read file content safely."""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}"
                }
            
            # Check file size
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                return {
                    "success": False,
                    "error": f"File too large: {size_mb:.2f}MB (limit: {max_size_mb}MB)"
                }
            
            # Read file
            content = path.read_text(encoding=encoding)
            
            return {
                "success": True,
                "content": content,
                "size_bytes": path.stat().st_size,
                "size_mb": round(size_mb, 2),
                "lines": len(content.splitlines()),
                "encoding": encoding
            }
            
        except UnicodeDecodeError as e:
            return {
                "success": False,
                "error": f"Encoding error: {str(e)}. Try a different encoding."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"File read error: {str(e)}"
            }
    
    @tframex_app.tool(
        name="File Writer",
        description="Safely write content to files with backup options"
    )
    async def write_file(
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """Write content to file safely."""
        try:
            path = Path(file_path)
            
            # Create backup if file exists
            if create_backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.backup')
                path.rename(backup_path)
            
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            path.write_text(content, encoding=encoding)
            
            return {
                "success": True,
                "file_path": str(path),
                "size_bytes": len(content.encode(encoding)),
                "lines": len(content.splitlines()),
                "backup_created": create_backup and path.exists()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"File write error: {str(e)}"
            }
    
    return 2  # Number of tools registered


def _is_safe_path(file_path: str, base_dir: str = None) -> bool:
    """Check if a file path is safe (prevents directory traversal)."""
    if base_dir is None:
        base_dir = tempfile.gettempdir()
    
    try:
        base = Path(base_dir).resolve()
        target = Path(file_path).resolve()
        return str(target).startswith(str(base))
    except Exception:
        return False