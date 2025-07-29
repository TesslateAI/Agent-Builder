#!/usr/bin/env python3
"""
Development start script for Agent-Builder with hot reloading and enhanced logging
Provides automatic restart on file changes and detailed logging output
"""

import os
import sys
import subprocess
import shutil
import time
import logging
import threading
from pathlib import Path
from datetime import datetime

# Try to import watchdog, install if not available
def try_import_watchdog():
    """Try to import watchdog and return availability status"""
    try:
        # Try importing directly to force reload from venv
        import sys
        if '.venv' in sys.prefix or '.venv' in sys.executable:
            # We're in a virtual environment, try importing
            import importlib
            import importlib.util
            
            # Force reimport by clearing from cache if exists
            for mod in ['watchdog', 'watchdog.observers', 'watchdog.events']:
                if mod in sys.modules:
                    del sys.modules[mod]
            
            importlib.import_module('watchdog.observers')
            importlib.import_module('watchdog.events')
            return True
        else:
            import importlib
            importlib.import_module('watchdog.observers')  
            importlib.import_module('watchdog.events')
            return True
    except ImportError:
        return False

WATCHDOG_AVAILABLE = try_import_watchdog()
Observer = None
FileSystemEventHandler = None

if WATCHDOG_AVAILABLE:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_info(message, color=Colors.BLUE):
    """Log info message with color"""
    logger.info(f"{color}{message}{Colors.ENDC}")

def log_success(message):
    """Log success message in green"""
    logger.info(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def log_error(message):
    """Log error message in red"""
    logger.error(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def log_warning(message):
    """Log warning message in yellow"""
    logger.warning(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def log_header(message):
    """Log header message"""
    logger.info(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}{Colors.BOLD}{message.center(60)}{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")

def create_file_change_handler(restart_callback, ignore_patterns=None):
    """Create file change handler based on availability of watchdog"""
    if not WATCHDOG_AVAILABLE or not FileSystemEventHandler:
        return None
    
    class FileChangeHandler(FileSystemEventHandler):
        """Handle file changes for hot reloading"""
        def __init__(self):
            super().__init__()
            self.restart_callback = restart_callback
            self.ignore_patterns = ignore_patterns or [
                '*.pyc', '__pycache__', '.git', '.venv', 'node_modules',
                '*.log', '*.tmp', '.env', 'dist', 'build'
            ]
            self.last_restart = time.time()
            self.restart_delay = 1.0  # Debounce file changes

        def should_ignore(self, path):
            """Check if path should be ignored"""
            path_str = str(path)
            for pattern in self.ignore_patterns:
                if pattern in path_str:
                    return True
            return False

        def on_modified(self, event):
            if event.is_directory or self.should_ignore(event.src_path):
                return
            
            # Debounce rapid file changes
            current_time = time.time()
            if current_time - self.last_restart < self.restart_delay:
                return
            
            self.last_restart = current_time
            log_warning(f"File changed: {event.src_path}")
            log_info("🔄 Restarting application...", Colors.CYAN)
            self.restart_callback()
    
    return FileChangeHandler()

class ProcessManager:
    """Manage backend and frontend processes"""
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.observer = None
        self.running = False

    def run_command(self, cmd, cwd=None, check=True):
        """Run a command and handle errors gracefully"""
        try:
            # For Git Bash/MINGW64, use bash -c instead of shell=True
            is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
            
            if isinstance(cmd, str) and is_mingw:
                # Use bash -c for command strings in MINGW64
                result = subprocess.run(['bash', '-c', cmd], cwd=cwd, check=check, 
                                      capture_output=False, text=True)
            elif isinstance(cmd, str):
                result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                                      capture_output=False, text=True)
            else:
                result = subprocess.run(cmd, cwd=cwd, check=check, 
                                      capture_output=False, text=True)
            return result
        except subprocess.CalledProcessError as e:
            log_error(f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            log_error(f"Error: {e}")
            sys.exit(1)

    def check_dependencies(self):
        """Check if required dependencies are installed"""
        log_info("🔍 Checking dependencies...", Colors.CYAN)
        
        # Check for uv
        if not shutil.which("uv"):
            log_error("uv package manager not found. Installing...")
            self.install_uv()
        
        # Check for npm
        if not shutil.which("npm"):
            log_error("npm not found. Please install Node.js first.")
            sys.exit(1)
        
        log_success("All dependencies checked")

    def install_watchdog_if_needed(self):
        """Install watchdog if not available and venv exists"""
        global WATCHDOG_AVAILABLE, Observer, FileSystemEventHandler
        
        if not WATCHDOG_AVAILABLE and Path(".venv").exists():
            log_warning("Installing watchdog for hot reload support...")
            try:
                # Check if we're in Git Bash/MINGW64 environment
                is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
                
                if is_mingw or os.name != 'nt':
                    cmd = "source .venv/Scripts/activate && pip install watchdog"
                else:
                    cmd = ".venv\\Scripts\\activate && pip install watchdog"
                self.run_command(cmd)
                
                # Try to import again
                if try_import_watchdog():
                    WATCHDOG_AVAILABLE = True
                    from watchdog.observers import Observer
                    from watchdog.events import FileSystemEventHandler
                    log_success("Watchdog installed successfully")
                else:
                    raise ImportError("Watchdog still not available after installation")
                
            except Exception as e:
                log_warning(f"Could not install watchdog: {e}")
                log_warning("Hot reload will be disabled")
        elif WATCHDOG_AVAILABLE:
            log_success("Watchdog already available")

    def install_uv(self):
        """Install uv package manager"""
        log_info("📦 Installing uv package manager...", Colors.CYAN)
        if os.name == 'nt':
            self.run_command("powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        else:
            self.run_command("curl -LsSf https://astral.sh/uv/install.sh | sh")
        
        # Add to PATH
        cargo_bin = os.path.expanduser("~/.cargo/bin")
        if cargo_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{cargo_bin}{os.pathsep}{os.environ.get('PATH', '')}"

    def setup_venv(self):
        """Set up Python virtual environment and install dependencies"""
        venv_path = Path(".venv")
        
        if not venv_path.exists():
            log_info("🔧 Creating Python virtual environment...", Colors.CYAN)
            self.run_command(["uv", "venv"])
            
            # Install dependencies
            self.install_dependencies()
        else:
            log_info("📦 Updating dependencies...", Colors.CYAN)
            self.update_dependencies()

    def install_dependencies(self):
        """Install all required dependencies"""
        global WATCHDOG_AVAILABLE, Observer, FileSystemEventHandler
        log_info("📦 Installing TFrameX from local folder...", Colors.CYAN)
        
        # Check if we're in Git Bash/MINGW64 environment
        is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
        
        if is_mingw or os.name != 'nt':
            activate = "source .venv/Scripts/activate"
        else:
            activate = ".venv\\Scripts\\activate"
        
        # Install TFrameX
        self.run_command(f"{activate} && uv pip install -e ../TFrameX")
        
        # Install TFrameX dependencies
        log_info("📦 Installing TFrameX dependencies...", Colors.CYAN)
        self.run_command(f"{activate} && uv pip install mcp openai")
        
        # Install Agent-Builder dependencies
        log_info("📦 Installing Agent-Builder dependencies...", Colors.CYAN)
        deps = '"flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp watchdog'
        self.run_command(f"{activate} && uv pip install {deps}")
        
        # Try to import watchdog again after installation
        try:
            if try_import_watchdog():
                WATCHDOG_AVAILABLE = True
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler
        except ImportError:
            pass
        
        log_success("All Python dependencies installed")

    def update_dependencies(self):
        """Update TFrameX from local folder"""
        global WATCHDOG_AVAILABLE, Observer, FileSystemEventHandler
        # Check if we're in Git Bash/MINGW64 environment
        is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
        
        if is_mingw or os.name != 'nt':
            activate = "source .venv/Scripts/activate"
        else:
            activate = ".venv\\Scripts\\activate"
        
        # Reinstall TFrameX to get latest changes
        self.run_command(f"{activate} && uv pip install -e ../TFrameX --force-reinstall --no-deps")
        
        # Ensure all dependencies are up to date
        deps = 'mcp openai "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp watchdog'
        self.run_command(f"{activate} && uv pip install {deps}")
        
        # Try to import watchdog again after update
        try:
            if try_import_watchdog():
                WATCHDOG_AVAILABLE = True
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler
        except ImportError:
            pass

    def setup_frontend(self):
        """Install frontend dependencies"""
        frontend_path = Path("builder/frontend")
        node_modules = frontend_path / "node_modules"
        
        if not node_modules.exists():
            log_info("📦 Installing frontend dependencies...", Colors.CYAN)
            # Check if we're in Git Bash/MINGW64 environment for npm command
            is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
            
            if is_mingw:
                cmd = ["npm.cmd", "install"]
            else:
                cmd = ["npm", "install"]
            
            self.run_command(cmd, cwd=frontend_path)
            log_success("Frontend dependencies installed")
        else:
            log_info("✅ Frontend dependencies already installed", Colors.GREEN)

    def start_backend(self):
        """Start the Flask backend with hot reloading"""
        log_info("🚀 Starting backend server...", Colors.CYAN)
        
        backend_path = Path("builder/backend")
        root_path = Path.cwd()
        
        # Set environment variables for Flask development
        env = os.environ.copy()
        env['FLASK_ENV'] = 'development'
        env['FLASK_DEBUG'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        
        # Check if we're in Git Bash/MINGW64 environment
        is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
        
        if is_mingw or os.name != 'nt':
            venv_python = root_path / ".venv" / "Scripts" / "python.exe"
            cmd = [str(venv_python), "app.py"]
        else:
            venv_python = root_path / ".venv" / "Scripts" / "python.exe"
            cmd = [str(venv_python), "app.py"]
        
        self.backend_process = subprocess.Popen(
            cmd, cwd=backend_path, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1
        )
        
        # Start logging thread for backend
        threading.Thread(
            target=self.log_process_output,
            args=(self.backend_process, "BACKEND"),
            daemon=True
        ).start()
        
        log_success("Backend started on http://localhost:5000")

    def start_frontend(self):
        """Start the frontend development server"""
        log_info("🚀 Starting frontend development server...", Colors.CYAN)
        
        frontend_path = Path("builder/frontend")
        
        # Check if we're in Git Bash/MINGW64 environment for npm command
        is_mingw = 'MINGW64' in os.environ.get('MSYSTEM', '') or 'mingw64' in os.environ.get('PATH', '').lower()
        
        if is_mingw:
            # Use npm.cmd on Windows in Git Bash
            cmd = ["npm.cmd", "run", "dev"]
        else:
            cmd = ["npm", "run", "dev"]
        
        # Start Vite dev server
        self.frontend_process = subprocess.Popen(
            cmd, cwd=frontend_path,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1
        )
        
        # Start logging thread for frontend
        threading.Thread(
            target=self.log_process_output,
            args=(self.frontend_process, "FRONTEND"),
            daemon=True
        ).start()
        
        log_success("Frontend development server starting...")

    def log_process_output(self, process, prefix):
        """Log output from a subprocess"""
        color = Colors.CYAN if prefix == "BACKEND" else Colors.GREEN
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"{color}[{prefix}]{Colors.ENDC} {line.rstrip()}")

    def setup_file_watcher(self):
        """Set up file watcher for hot reloading"""
        if not WATCHDOG_AVAILABLE:
            log_warning("Hot reload disabled - watchdog not available")
            log_info("Install with: pip install watchdog", Colors.YELLOW)
            return
        
        log_info("👁️  Setting up file watcher for hot reloading...", Colors.CYAN)
        
        try:
            self.observer = Observer()
            handler = create_file_change_handler(self.restart_backend)
            
            if handler is None:
                log_warning("Could not create file change handler")
                return
            
            # Watch backend files
            backend_path = Path("builder/backend")
            self.observer.schedule(handler, str(backend_path), recursive=True)
            
            # Watch TFrameX files
            tframex_path = Path("../TFrameX")
            if tframex_path.exists():
                self.observer.schedule(handler, str(tframex_path), recursive=True)
            
            self.observer.start()
            log_success("File watcher started")
        except Exception as e:
            log_warning(f"Could not start file watcher: {e}")
            log_warning("Hot reload will be disabled")

    def restart_backend(self):
        """Restart the backend process"""
        if self.backend_process:
            log_info("Stopping backend...", Colors.YELLOW)
            self.backend_process.terminate()
            self.backend_process.wait()
        
        time.sleep(0.5)  # Brief pause before restart
        self.start_backend()

    def stop_all(self):
        """Stop all processes"""
        self.running = False
        
        if self.observer:
            log_info("Stopping file watcher...", Colors.YELLOW)
            self.observer.stop()
            self.observer.join()
        
        if self.backend_process:
            log_info("Stopping backend...", Colors.YELLOW)
            self.backend_process.terminate()
            self.backend_process.wait()
        
        if self.frontend_process:
            log_info("Stopping frontend...", Colors.YELLOW)
            self.frontend_process.terminate()
            self.frontend_process.wait()

    def run(self):
        """Main run method"""
        try:
            log_header("Agent-Builder Development Server")
            log_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_info(f"Using TFrameX from: ../TFrameX")
            
            # Check dependencies
            self.check_dependencies()
            
            # Setup environment
            self.setup_venv()
            self.install_watchdog_if_needed()
            self.setup_frontend()
            
            # Start services
            self.start_backend()
            self.start_frontend()
            self.setup_file_watcher()
            
            # Display access info
            print("\n")
            log_success("🎉 Agent-Builder is running!")
            log_info("📍 Backend: http://localhost:5000", Colors.CYAN)
            log_info("📍 Frontend: http://localhost:5173", Colors.CYAN)
            log_info("🔄 Hot reload enabled - changes will restart automatically", Colors.YELLOW)
            log_info("Press Ctrl+C to stop", Colors.YELLOW)
            print("\n")
            
            self.running = True
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n")
            log_warning("Shutting down...")
            self.stop_all()
            log_success("Agent-Builder stopped")
            sys.exit(0)
        except Exception as e:
            log_error(f"An error occurred: {e}")
            self.stop_all()
            sys.exit(1)

def main():
    """Main entry point"""
    manager = ProcessManager()
    manager.run()

if __name__ == "__main__":
    main()