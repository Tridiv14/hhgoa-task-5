import speech_recognition as sr
import pyttsx3
import threading
import subprocess
import os

class TTSEngine:
    """Independent Text-to-Speech Engine."""
    def __init__(self):
        self._tts_failed = False
        
    def speak(self, text: str):
        # Fallback to text-only if TTS previously crashed
        if self._tts_failed:
            return
            
        def _speak():
            try:
                # Run PyTTSx3 in a totally isolated subprocess to completely avoid 
                # PySide6 threading conflicts and 'run loop already started' COM errors.
                script = "import pyttsx3, sys\\nengine = pyttsx3.init()\\ntext = sys.stdin.read()\\nif text:\\n    engine.say(text)\\n    engine.runAndWait()"
                
                flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(
                    ['python', '-c', script],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=flags
                )
                process.communicate(input=text.encode('utf-8'))
            except Exception as e:
                print(f"TTS Error: {e}")
                self._tts_failed = True 
                
        t = threading.Thread(target=_speak)
        t.daemon = True
        t.start()


class STTEngine:
    """Independent Speech-to-Text Engine."""
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
    def listen_once(self, timeout=5) -> str:
        """Listens for a single utterance and returns the recognized text."""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except Exception as e:
                print(f"STT Error: {e}")
                return ""
