from llm import OllamaProvider
from tools import JarvisTools
from audio import TTSEngine, STTEngine

class JarvisController:
    def __init__(self, ui_callback, confirm_callback):
        self.ui_callback = ui_callback
        self.confirm_callback = confirm_callback
        self.llm = OllamaProvider(model_name="llama3.2:1b")
        self.tts = TTSEngine()
        self.stt = STTEngine()
        self.voice_enabled = False
        
    def process_text_input(self, text: str):
        if self.ui_callback:
            self.ui_callback("System", "Thinking...")
            
        tools_instance = JarvisTools(self.confirm_callback)
        
        tools_schema = [
            # File System
            {"type": "function", "function": {"name": "list_dir", "description": "Lists directory contents in workspace", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "read_file", "description": "Reads a file in workspace", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}},
            {"type": "function", "function": {"name": "create_file", "description": "Creates a file in workspace", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]}}},
            {"type": "function", "function": {"name": "create_dir", "description": "Creates a directory in workspace", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "modify_file", "description": "Appends text to a file in workspace", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]}}},
            
            # System
            {"type": "function", "function": {"name": "get_system_info", "description": "Returns basic system info", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "run_terminal_command", "description": "Runs a terminal command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
            
            # Apps & Web
            {"type": "function", "function": {"name": "open_application", "description": "Opens installed apps (e.g. chrome, notepad)", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
            {"type": "function", "function": {"name": "web_search", "description": "Searches Google or YouTube", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "engine": {"type": "string", "enum": ["google", "youtube"]}}, "required": ["query", "engine"]}}},
            {"type": "function", "function": {"name": "spotify_search", "description": "Searches and plays music on Spotify", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}
        ]
        
        response, tool_calls = self.llm.generate_response(text, tools=tools_schema)
        
        while tool_calls:
            for tool_call in tool_calls:
                # ollama python client returns objects for function and arguments if it's a model
                try:
                    func = tool_call.function
                    func_name = func.name
                    args = func.arguments
                except AttributeError:
                    func_name = tool_call.get('function', {}).get('name')
                    args = tool_call.get('function', {}).get('arguments', {})
                
                args = args or {}
                
                if self.ui_callback:
                    self.ui_callback("System", f"Executing tool: {func_name}...")
                
                result = ""
                # File System Route
                if func_name == "list_dir": result = tools_instance.list_dir(args.get("path", "."))
                elif func_name == "read_file": result = tools_instance.read_file(args.get("filepath", ""))
                elif func_name == "create_file": result = tools_instance.create_file(args.get("filepath", ""), args.get("content", ""))
                elif func_name == "create_dir": result = tools_instance.create_dir(args.get("path", ""))
                elif func_name == "modify_file": result = tools_instance.modify_file(args.get("filepath", ""), args.get("content", ""))
                # System Route
                elif func_name == "get_system_info": result = tools_instance.get_system_info()
                elif func_name == "run_terminal_command": result = tools_instance.run_terminal_command(args.get("command", ""))
                # App & Web Route
                elif func_name == "open_application": result = tools_instance.open_application(args.get("app_name", ""))
                elif func_name == "web_search": result = tools_instance.web_search(args.get("query", ""), args.get("engine", "google"))
                elif func_name == "spotify_search": result = tools_instance.spotify_search(args.get("query", ""))
                    
                # Send result back to LLM messages
                self.llm.messages.append({"role": "tool", "content": f"{result}"})
                
            # Request LLM again with tool results
            response, tool_calls = self.llm.generate_response(tools=tools_schema, skip_append=True)
                
        if self.ui_callback:
            if response:
                self.ui_callback("Jarvis", response)
                if self.voice_enabled:
                    self.tts.speak(response)
            else:
                self.ui_callback("Jarvis", "(No response generated)")
        
    def set_voice_mode(self, enabled: bool):
        self.voice_enabled = enabled
