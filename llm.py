import ollama
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseProvider(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    def generate_response(
        self, 
        user_input: str = "", 
        tools: List[Dict[str, Any]] = None, 
        is_tool_result: bool = False, 
        skip_append: bool = False
    ) -> Tuple[str, List[Any]]:
        """Generates a response from the language model.
        Returns a tuple of (text_response, tool_calls_list)."""
        pass

class OllamaProvider(BaseProvider):
    """Concrete implementation for local Ollama models."""
    
    def __init__(self, model_name="llama3.2:1b", max_history=15):
        self.model_name = model_name
        self.max_history = max_history
        self.system_prompt = {
            "role": "system", 
            "content": "You are Jarvis, a concise, helpful, and cheerful desktop AI assistant."
        }
        self.messages = [self.system_prompt]
        
    def _trim_history(self):
        """Maintains a lightweight conversation history to prevent context overflow."""
        # We always keep the system prompt at index 0.
        if len(self.messages) > self.max_history + 1:
            self.messages = [self.system_prompt] + self.messages[-(self.max_history):]

    def generate_response(self, user_input: str = "", tools=None, is_tool_result=False, skip_append=False):
        if not skip_append and user_input:
            if is_tool_result:
                self.messages.append({"role": "tool", "content": user_input})
            else:
                self.messages.append({"role": "user", "content": user_input})
                
        self._trim_history()
            
        try:
            kwargs = {
                "model": self.model_name,
                "messages": self.messages
            }
            if tools:
                kwargs["tools"] = tools
                
            response = ollama.chat(**kwargs)
            
            ai_reply = response.get('message', {}).get('content', '')
            tool_calls = response.get('message', {}).get('tool_calls', [])
            
            # Store the assistant's turn in history
            if not tool_calls:
                self.messages.append({"role": "assistant", "content": ai_reply})
            else:
                self.messages.append(response.get('message', {}))
                
            self._trim_history()
                
            return ai_reply, tool_calls
            
        except ollama.ResponseError as e:
            error_msg = f"Ollama model error: {e}"
            print(error_msg)
            return "My thought process encountered an error. Let's try that again.", []
        except Exception as e:
            error_msg = f"Connection failure: {e}"
            print(error_msg)
            return "I cannot connect to my brain! Please ensure Ollama is running locally.", []
