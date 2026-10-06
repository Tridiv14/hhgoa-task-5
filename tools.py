import os
import psutil
import platform
import subprocess
import webbrowser
from typing import Callable

class JarvisTools:
    def __init__(self, confirmation_callback: Callable[[str], bool]):
        self.confirmation_callback = confirmation_callback
        # Restrict operations to the current working directory
        self.workspace = os.path.abspath(os.getcwd())

    def _is_safe_path(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.workspace)

    # --- File System Operations ---
    def list_dir(self, path: str = ".") -> str:
        """Lists contents of a directory within the workspace."""
        if not self._is_safe_path(path):
            return "Error: Path is outside the restricted workspace."
        try:
            items = os.listdir(path)
            return "\n".join(items) if items else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    def read_file(self, filepath: str) -> str:
        """Reads a file and returns its content."""
        if not self._is_safe_path(filepath):
            return "Error: Path is outside the restricted workspace."
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' not found."
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def create_file(self, filepath: str, content: str) -> str:
        if not self._is_safe_path(filepath):
            return "Error: Path is outside the restricted workspace."
        msg = f"Jarvis wants to create a file at {filepath}. Allow?"
        if not self.confirmation_callback(msg): 
            return "User aborted."
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File '{filepath}' created successfully."
        except Exception as e:
            return f"Error creating file: {e}"

    def create_dir(self, path: str) -> str:
        if not self._is_safe_path(path):
            return "Error: Path is outside the restricted workspace."
        msg = f"Jarvis wants to create directory at {path}. Allow?"
        if not self.confirmation_callback(msg): 
            return "User aborted."
        try:
            os.makedirs(path, exist_ok=True)
            return f"Directory '{path}' created successfully."
        except Exception as e:
            return f"Error creating directory: {e}"

    def modify_file(self, filepath: str, content: str) -> str:
        if not self._is_safe_path(filepath):
            return "Error: Path is outside the restricted workspace."
        msg = f"Jarvis wants to append to file at {filepath}. Allow?"
        if not self.confirmation_callback(msg): 
            return "User aborted."
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write("\n" + content)
            return f"File '{filepath}' modified successfully."
        except Exception as e:
            return f"Error modifying file: {e}"

    # --- System Information & Execution ---
    def get_system_info(self) -> str:
        """Returns detailed system information including CPU, memory, disk, network, and GPU."""
        info = {
            "OS": f"{platform.system()} {platform.release()} ({platform.version()})",
            "CPU": f"{platform.processor()} (Usage: {psutil.cpu_percent(interval=1)}%)",
            "Memory": f"Usage: {psutil.virtual_memory().percent}% (Total: {psutil.virtual_memory().total / (1024**3):.2f} GB)"
        }
        
        try:
            disk = psutil.disk_usage(self.workspace)
            info["Disk (Workspace)"] = f"Usage: {disk.percent}% (Free: {disk.free / (1024**3):.2f} GB)"
        except: pass
        
        try:
            net = psutil.net_io_counters()
            info["Network"] = f"Sent: {net.bytes_sent / (1024**2):.2f} MB, Received: {net.bytes_recv / (1024**2):.2f} MB"
        except: pass
        
        try:
            # Attempt to query NVIDIA GPU
            gpu_result = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader"], capture_output=True, text=True)
            if gpu_result.stdout:
                info["GPU (NVIDIA)"] = gpu_result.stdout.strip()
        except: pass
        
        return "\n".join([f"{k}: {v}" for k, v in info.items()])

    def run_terminal_command(self, command: str) -> str:
        """Runs a terminal command safely within the workspace after confirmation."""
        cmd_lower = command.lower()
        
        # 1. Block obviously dangerous commands outright
        forbidden = ["format c:", "del /s /q c:\\", "rm -rf /", "diskpart"]
        for f in forbidden:
            if f in cmd_lower:
                return "Error: Command outright blocked due to hardcoded security rules."
                
        # 2. Check for destructive operations to give an explicit warning
        destructive_keywords = ["del", "rm", "rmdir", "drop", "truncate"]
        is_destructive = any(k in cmd_lower.split() for k in destructive_keywords)
        
        if is_destructive:
            msg = f"⚠️ DANGER: Jarvis wants to execute a DESTRUCTIVE command:\n\n{command}\n\nAre you absolutely sure?"
        else:
            msg = f"Jarvis wants to execute:\n\n{command}\n\nAllow?"
            
        if not self.confirmation_callback(msg):
            return "Command execution aborted by user."
            
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=self.workspace
            )
            output = result.stdout
            if result.stderr:
                output += f"\nErrors:\n{result.stderr}"
            return output if output else "Command executed successfully with no output."
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"
            
    # --- App and Web Integrations ---
    def open_application(self, app_name: str) -> str:
        """Opens an installed application like Chrome on Windows."""
        msg = f"Jarvis wants to open the application: {app_name}. Allow?"
        if not self.confirmation_callback(msg): 
            return "User aborted."
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Attempted to open application: {app_name}"
        except Exception as e:
            return f"Error opening application: {e}"

    def web_search(self, query: str, engine: str = "google") -> str:
        """Performs a web search using Google or YouTube."""
        try:
            if engine.lower() == "youtube":
                url = f"https://www.youtube.com/results?search_query={query}"
            else:
                url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return f"Performed {engine} search for: '{query}'"
        except Exception as e:
            return f"Error performing web search: {e}"

    def spotify_search(self, query: str) -> str:
        """Opens Spotify and searches for a specific track/artist."""
        try:
            url = f"spotify:search:{query}"
            os.startfile(url)
            return f"Opened Spotify searching for: '{query}'"
        except Exception as e:
            return f"Error opening Spotify (make sure the desktop app is installed): {e}"
