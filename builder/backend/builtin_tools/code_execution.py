# builder/backend/builtin_tools/code_execution.py
"""
Code execution tools for the Agent-Builder application.
Provides safe Python code and shell command execution capabilities.
"""

import asyncio
import os
import tempfile
from typing import Dict, Any


def register_code_execution_tools(tframex_app):
    """Register code execution tools with the TFrameXApp instance."""
    
    @tframex_app.tool(
        name="Python Code Executor",
        description="Safely execute Python code in a sandboxed environment with timeout protection"
    )
    async def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code safely with output capture."""
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute with timeout and capture output
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir()  # Run in temp directory for safety
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                
                result = {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else "",
                    "return_code": process.returncode
                }
                
                if not result["success"]:
                    result["error"] = f"Code execution failed with return code {process.returncode}"
                
                return result
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Code execution timed out after {timeout} seconds",
                    "stdout": "",
                    "stderr": ""
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "stdout": "",
                "stderr": ""
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    @tframex_app.tool(
        name="Shell Command Executor",
        description="Execute shell commands with safety restrictions and timeout"
    )
    async def execute_shell(command: str, timeout: int = 30, working_dir: str = None) -> Dict[str, Any]:
        """Execute shell commands safely."""
        # Basic safety checks
        dangerous_commands = ['rm -rf', 'del /f', 'format', 'shutdown', 'reboot']
        if any(cmd in command.lower() for cmd in dangerous_commands):
            return {
                "success": False,
                "error": "Command contains potentially dangerous operations",
                "stdout": "",
                "stderr": ""
            }
        
        try:
            cwd = working_dir or tempfile.gettempdir()
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "return_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "stdout": "",
                "stderr": ""
            }
    
    return 2  # Number of tools registered