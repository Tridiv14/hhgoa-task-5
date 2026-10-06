import sys
import psutil
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QMessageBox, QLabel, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from jarvis import JarvisController

class WorkerThread(QThread):
    """Handles LLM and tool execution without blocking the UI thread."""
    response_signal = Signal(str, str)
    confirm_signal = Signal(str)
    status_signal = Signal(str)
    
    def __init__(self, controller, text):
        super().__init__()
        self.controller = controller
        self.text = text
        self.confirm_event = threading.Event()
        self.confirm_result = False
        
    def request_confirmation(self, msg: str) -> bool:
        self.confirm_event.clear()
        self.confirm_signal.emit(msg)
        self.confirm_event.wait()
        return self.confirm_result
        
    def run(self):
        self.status_signal.emit("THINKING")
        original_callback = self.controller.ui_callback
        
        # Intercept UI callbacks to update HUD tool activity dynamically
        def custom_callback(sender, msg):
            if sender == "System" and "Executing tool" in msg:
                self.status_signal.emit("EXECUTING")
            self.response_signal.emit(sender, msg)
            
        self.controller.ui_callback = custom_callback
        self.controller.process_text_input(self.text)
        self.controller.ui_callback = original_callback
        self.status_signal.emit("IDLE")


class PTTWorkerThread(QThread):
    """Handles Speech Recognition asynchronously."""
    text_recognized = Signal(str)
    
    def __init__(self, stt_engine):
        super().__init__()
        self.stt_engine = stt_engine
        
    def run(self):
        text = self.stt_engine.listen_once(timeout=10)
        if text:
            self.text_recognized.emit(text)


class JarvisHUD(QMainWindow):
    """Futuristic Dark Developer HUD interface for Jarvis."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS HUD - Developer Interface")
        self.resize(950, 750)
        
        # Deep space dark background, high contrast text, monospace dev font
        self.setStyleSheet("background-color: #0a0a0f; color: #E0E0E0; font-family: 'Consolas', 'Courier New', monospace;")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)
        
        # --- 1. TOP HUD BAR ---
        self.hud_layout = QHBoxLayout()
        
        self.sys_stats_label = QLabel("[SYS: CPU --% | RAM --%]")
        self.sys_stats_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 15px;")
        
        self.status_label = QLabel("JARVIS: IDLE")
        self.status_label.setStyleSheet("color: #00FF9D; font-weight: bold; font-size: 18px; letter-spacing: 2px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        self.mic_label = QLabel("[MIC: OFF]")
        self.mic_label.setStyleSheet("color: #FF2A2A; font-weight: bold; font-size: 15px;")
        self.mic_label.setAlignment(Qt.AlignRight)
        
        self.hud_layout.addWidget(self.sys_stats_label)
        self.hud_layout.addWidget(self.status_label, stretch=1)
        self.hud_layout.addWidget(self.mic_label)
        self.main_layout.addLayout(self.hud_layout)
        
        # Divider Line
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setStyleSheet("background-color: #1a1a2e; max-height: 2px;")
        self.main_layout.addWidget(div1)
        
        # --- 2. CONVERSATION HISTORY ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #11111a;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
                padding: 15px;
                font-size: 15px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: #0a0a0f;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #1a1a2e;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        self.main_layout.addWidget(self.chat_display, stretch=1)
        
        # --- 3. TOOL ACTIVITY ---
        self.tool_activity_label = QLabel(">_ SYSTEM: Ready")
        self.tool_activity_label.setStyleSheet("color: #FFB800; font-size: 13px; font-weight: bold; margin-bottom: 5px;")
        self.main_layout.addWidget(self.tool_activity_label)
        
        # --- 4. COMMAND INPUT AREA ---
        self.input_layout = QHBoxLayout()
        self.input_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter command sequence...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #11111a;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
                padding: 12px;
                color: #00E5FF;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit:focus { border: 1px solid #00E5FF; }
        """)
        self.input_field.returnPressed.connect(self.handle_send)
        self.input_layout.addWidget(self.input_field, stretch=1)
        
        btn_style = """
            QPushButton {
                background-color: #11111a;
                border: 1px solid #1a1a2e;
                border-radius: 8px;
                padding: 12px 25px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #1a1a2e; border: 1px solid #00E5FF; color: #00E5FF; }
            QPushButton:pressed { background-color: #00E5FF; color: #000000; }
        """
        
        self.send_btn = QPushButton("SEND")
        self.send_btn.setStyleSheet(btn_style)
        self.send_btn.clicked.connect(self.handle_send)
        self.input_layout.addWidget(self.send_btn)
        
        self.ptt_btn = QPushButton("🎙️ PTT")
        self.ptt_btn.setStyleSheet(btn_style)
        self.ptt_btn.clicked.connect(self.do_push_to_talk)
        self.input_layout.addWidget(self.ptt_btn)
        
        self.main_layout.addLayout(self.input_layout)
        
        # --- INITIALIZATION ---
        self.controller = JarvisController(ui_callback=None, confirm_callback=None)
        
        # System Stats Poller (Non-blocking QTimer)
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_sys_stats)
        self.stats_timer.start(2000) # Poll every 2 seconds
        self.update_sys_stats()
        
        self.append_message("System", "Jarvis Neural Link established.")

    def update_sys_stats(self):
        """Updates the system stats indicator asynchronously."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.sys_stats_label.setText(f"[SYS: CPU {cpu:04.1f}% | RAM {ram:04.1f}%]")

    def append_message(self, sender: str, message: str):
        """Renders incoming messages beautifully to the conversation history."""
        if sender == "System":
            # Show system/tool actions in the dedicated Tool Activity area
            self.tool_activity_label.setText(f">_ SYSTEM: {message}")
            if "Executing tool" not in message:
                self.chat_display.append(f"<span style='color: #6a6a8a;'><i>[SYS] {message}</i></span><br>")
        elif sender == "You":
            self.chat_display.append(f"<span style='color: #00E5FF;'><b>[USER]:</b></span> <span style='color: #E0E0E0;'>{message}</span><br>")
        elif sender == "Jarvis":
            self.chat_display.append(f"<span style='color: #00FF9D;'><b>[JARVIS]:</b></span> <span style='color: #FFFFFF;'>{message}</span><br>")
        
        # Auto-scroll
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_status(self, status: str):
        """Updates the central Jarvis status indicator and manages input states."""
        self.status_label.setText(f"JARVIS: {status}")
        if status == "IDLE":
            self.status_label.setStyleSheet("color: #00FF9D; font-weight: bold; font-size: 18px; letter-spacing: 2px;")
            self.input_field.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.ptt_btn.setEnabled(True)
            self.input_field.setFocus()
        elif status == "THINKING":
            self.status_label.setStyleSheet("color: #FFB800; font-weight: bold; font-size: 18px; letter-spacing: 2px;")
            self.input_field.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.ptt_btn.setEnabled(False)
        elif status == "EXECUTING":
            self.status_label.setStyleSheet("color: #FF2A2A; font-weight: bold; font-size: 18px; letter-spacing: 2px;")

    def handle_send(self):
        """Fires the command securely via QThread."""
        text = self.input_field.text().strip()
        if text:
            self.append_message("You", text)
            self.input_field.clear()
            
            # Spin up a worker thread to ensure the UI NEVER blocks
            self.worker = WorkerThread(self.controller, text)
            self.controller.confirm_callback = self.worker.request_confirmation
            
            self.worker.response_signal.connect(self.append_message)
            self.worker.status_signal.connect(self.update_status)
            self.worker.confirm_signal.connect(self.show_confirmation_dialog)
            self.worker.start()

    def show_confirmation_dialog(self, msg: str):
        """Shows a blocking confirmation dialog on the main UI thread securely via Signals."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("⚠️ SECURITY OVERRIDE REQUIRED")
        dlg.setText(msg)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)
        
        # Match HUD styling for the popup
        dlg.setStyleSheet("""
            QMessageBox { background-color: #0a0a0f; color: #E0E0E0; font-family: 'Consolas'; font-size: 14px; }
            QPushButton { background-color: #1a1a2e; border: 1px solid #FF2A2A; color: #FFFFFF; padding: 5px 15px; border-radius: 3px; }
            QPushButton:hover { background-color: #FF2A2A; color: #000; }
        """)
        
        reply = dlg.exec()
        self.worker.confirm_result = (reply == QMessageBox.Yes)
        self.worker.confirm_event.set()

    def do_push_to_talk(self):
        """Activates the Microphone dynamically."""
        self.ptt_btn.setText("🔴 ACTV")
        self.ptt_btn.setEnabled(False)
        self.mic_label.setText("[MIC: ON]")
        self.mic_label.setStyleSheet("color: #00FF9D; font-weight: bold; font-size: 15px;")
        
        self.update_status("LISTENING")
        self.status_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 18px; letter-spacing: 2px;")
        
        # Temporarily enable voice generation for response
        self.controller.set_voice_mode(True) 
        
        self.ptt_worker = PTTWorkerThread(self.controller.stt)
        self.ptt_worker.text_recognized.connect(self.handle_voice_input)
        self.ptt_worker.finished.connect(self.reset_ptt_btn)
        self.ptt_worker.start()
        
    def reset_ptt_btn(self):
        self.ptt_btn.setText("🎙️ PTT")
        self.ptt_btn.setEnabled(True)
        self.mic_label.setText("[MIC: OFF]")
        self.mic_label.setStyleSheet("color: #FF2A2A; font-weight: bold; font-size: 15px;")
        self.update_status("IDLE")
        
    def handle_voice_input(self, text: str):
        """Routes voice transcript cleanly through the standard text pipeline."""
        self.input_field.setText(text)
        self.handle_send()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = JarvisHUD()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
