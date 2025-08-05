#!/usr/bin/env python3
"""
Development start script for Agent-Builder using local TFrameX
Python equivalent of start-dev.sh for Windows/cross-platform usage
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a command and handle errors gracefully"""
    try:
        if isinstance(cmd, str):
            # For shell commands like activation
            result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                                  capture_output=False, text=True)
        else:
            # For list commands
            result = subprocess.run(cmd, cwd=cwd, check=check, 
                                  capture_output=False, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        print(f"Error: {e}")
        sys.exit(1)

def check_uv_installed():
    """Check if uv package manager is installed"""
    return shutil.which("uv") is not None

def install_uv():
    """Install uv package manager"""
    print("📦 Installing uv package manager...")
    if os.name == 'nt':  # Windows
        # Download and run the Windows installer
        run_command("powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
    else:  # Unix-like systems
        run_command("curl -LsSf https://astral.sh/uv/install.sh | sh")
    
    # Add to PATH for current session
    if os.name == 'nt':
        cargo_bin = os.path.expanduser("~/.cargo/bin")
    else:
        cargo_bin = os.path.expanduser("~/.cargo/bin")
    
    if cargo_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{cargo_bin}{os.pathsep}{os.environ.get('PATH', '')}"

def setup_venv():
    """Set up Python virtual environment and install dependencies"""
    venv_path = Path(".venv")
    
    if not venv_path.exists():
        print("🔧 Setting up Python environment...")
        run_command(["uv", "venv"])
        
        # Install TFrameX from local folder
        print("📦 Installing TFrameX from local folder...")
        if os.name == 'nt':
            activate_cmd = ".venv\\Scripts\\activate && uv pip install -e ../TFrameX"
        else:
            activate_cmd = "source .venv/bin/activate && uv pip install -e ../TFrameX"
        run_command(activate_cmd)
        
        # Install TFrameX dependencies first
        print("📦 Installing TFrameX dependencies...")
        if os.name == 'nt':
            deps_cmd = ".venv\\Scripts\\activate && uv pip install mcp openai"
        else:
            deps_cmd = "source .venv/bin/activate && uv pip install mcp openai"
        run_command(deps_cmd)
        
        # Install other dependencies
        print("📦 Installing Agent-Builder dependencies...")
        if os.name == 'nt':
            agent_deps_cmd = '.venv\\Scripts\\activate && uv pip install "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp'
        else:
            agent_deps_cmd = 'source .venv/bin/activate && uv pip install "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp'
        run_command(agent_deps_cmd)
        
    else:
        # Always reinstall TFrameX to get latest changes
        print("🔄 Updating TFrameX from local folder...")
        if os.name == 'nt':
            update_cmd = ".venv\\Scripts\\activate && uv pip install -e ../TFrameX --force-reinstall --no-deps"
        else:
            update_cmd = "source .venv/bin/activate && uv pip install -e ../TFrameX --force-reinstall --no-deps"
        run_command(update_cmd)
        
        # Ensure all dependencies are installed
        print("📦 Checking dependencies...")
        if os.name == 'nt':
            check_deps_cmd = '.venv\\Scripts\\activate && uv pip install mcp openai "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp'
        else:
            check_deps_cmd = 'source .venv/bin/activate && uv pip install mcp openai "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp'
        run_command(check_deps_cmd)

def build_frontend():
    """Build the frontend if not already built"""
    frontend_dist = Path("builder/frontend/dist")
    
    if not frontend_dist.exists():
        print("🏗️  Building frontend...")
        frontend_path = Path("builder/frontend")
        
        # Install npm dependencies if needed
        node_modules = frontend_path / "node_modules"
        if not node_modules.exists():
            run_command(["npm", "install"], cwd=frontend_path)
        
        # Build the frontend
        run_command(["npm", "run", "build"], cwd=frontend_path)
    else:
        print("✅ Frontend already built")

def start_application():
    """Start the Flask application"""
    print("")
    print("✅ Starting Agent-Builder!")
    print("   URL: http://localhost:5000")
    print("   Using TFrameX from: ../TFrameX")
    print("")
    print("Press Ctrl+C to stop")
    print("")
    
    backend_path = Path("builder/backend")
    root_path = Path.cwd()
    
    # Start the application with activated virtual environment
    # Need to use absolute path to venv since we're changing working directory
    if os.name == 'nt':
        venv_activate = root_path / ".venv" / "Scripts" / "activate"
        app_cmd = f'"{venv_activate}" && python app.py'
    else:
        venv_activate = root_path / ".venv" / "bin" / "activate"
        app_cmd = f'source "{venv_activate}" && python app.py'
    
    run_command(app_cmd, cwd=backend_path)

def main():
    """Main function to orchestrate the development environment setup"""
    print("🚀 Starting Agent-Builder with local TFrameX 1.1.0")
    print("=" * 42)
    
    try:
        # Check if uv is installed
        if not check_uv_installed():
            install_uv()
        
        # Setup virtual environment and dependencies
        setup_venv()
        
        # Build frontend
        build_frontend()
        
        # Start the application
        start_application()
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Agent-Builder...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
