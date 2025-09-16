import numpy as np
import os
import re
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QTextEdit, QFrame,
    QVBoxLayout, QHBoxLayout, QSizeGrip , QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon , QTextCursor , QClipboard
from halo.core.llm import query_ollama
from halo.core.pipeline import start_new_session, get_transcript_context, record_continuous
import threading
from halo.core.pipeline import get_transcript_context, _save_to_file
from halo.core.listener import stop_streaming
import ctypes


class LLMWorker(QThread):
    token_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, query_dict):
        super().__init__()
        self.prompt = query_dict["prompt"]
        self.model = query_dict.get("model", "qwen2.5:3b")  # default fallback
        self._stop_event = threading.Event()

    def run(self):
        try:
            for token in query_ollama(self.prompt, model=self.model, stream=True):
                if self._stop_event.is_set():
                    break
                self.token_received.emit(token)
            self.finished.emit()
        except Exception as e:
            self.token_received.emit(f"[Error] {str(e)}")
            self.finished.emit()

    def stop(self):  # <--- Method to stop streaming
        self._stop_event.set()


# ----------------- Clickable QLabel -----------------
class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()  # Custom signal
    def mousePressEvent(self, event):
        self.clicked.emit()

# ----------------- Chat Panel -----------------
class ChatPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._protect_window()

        self.setGeometry(1000, 100, 400, 500)
        self.drag_position = None

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background: rgba(17,17,17,180);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,50);
            }
        """)
        self.container.setGeometry(0,0,400,500)

        layout = QVBoxLayout()
        layout.setContentsMargins(16,16,16,16)
        layout.setSpacing(6)

        # Messages display
        # in your __init__:
        self.messages = []           # Python list for history
        # Inside ChatPanel.__init__(), replace the chat_box definition with:
        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setStyleSheet("""
            QTextEdit {
                background: rgba(17,17,17,180);  /* semi-transparent dark */
                color: #e5e5e5;
                font-family: "Fira Code", "Consolas", "Monaco", monospace;
                font-size: 13px;
                border: none;
                border-radius: 12px;
                padding: 8px;
                backdrop-filter: blur(8px);  /* blurry effect */
            }
            QTextEdit QScrollBar:vertical {
                width: 8px;
                background: rgba(0,0,0,0);
            }
            QTextEdit QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.3);
                border-radius: 4px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.5);
            }
        """)
        self.chat_box.setText("Halo is ready to assist you\n")
        layout.addWidget(self.chat_box, 1)

        self.chat_box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )

        # Suggestion label
        self.suggestion_label = ClickableLabel("💡 What should I say next?")
        self.suggestion_label.setStyleSheet("color: #ffcc00; font-weight: bold;")
        self.suggestion_label.clicked.connect(self.use_suggestion)
        layout.addWidget(self.suggestion_label)

        # Input area
        self.input = QTextEdit()
        self.input.setFixedHeight(40)
        self.input.setStyleSheet("""
            QTextEdit {
                background: rgba(255,255,255,30);
                border-radius: 12px;
                color: white;
            }
        """)
        layout.addWidget(self.input)

        self.model_selector = QComboBox()
        self.model_selector.addItems(["gemma3:4b", "qwen2.5:3b", "phi3"])
        self.model_selector.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,30);
                border-radius: 10px;
                color: white;
                padding: 4px;
            }
        """)
        layout.addWidget(self.model_selector)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                border-radius: 10px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a67d8; }
        """)

        self.copy_code_btn = QPushButton("Copy Last Code")
        self.copy_code_btn.setStyleSheet("background-color:#4ade80; color:black; border-radius:6px; padding:6px;")
        self.copy_code_btn.clicked.connect(self.copy_last_code_block)
        layout.addWidget(self.copy_code_btn)

        send_icon = QIcon(os.path.join("halo", "ui", "assets", "send.svg"))
        self.send_btn.setIcon(send_icon)
        self.send_btn.setIconSize(QtCore.QSize(20,20))
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        # Resize handle
        size_grip = QSizeGrip(self)
        layout.addWidget(size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.container.setLayout(layout)
    
    def _protect_window(self):
        """
        Prevent overlay from appearing in screen capture/screenshot.
        Works on Windows 10+.
        """
        try:
            hwnd = int(self.winId())  # Get native window handle
            user32 = ctypes.windll.user32

            # Constants
            WDA_NONE = 0x0
            WDA_MONITOR = 0x1
            WDA_EXCLUDEFROMCAPTURE = 0x11  # Best option (Win 10 2004+)

            # Try strongest protection first
            if not user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
                # Fallback for slightly older Windows
                user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)

            print("✅ Overlay protected from screenshots & screen share.")

        except Exception as e:
            print(f"⚠️ Could not protect overlay: {e}")


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_position and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    # ----------------- Sending message with context -----------------
    # in your __init__:
    def send_message(self):
        user_text = self.input.toPlainText().strip()
        if not user_text:
            return

        # Include incremental transcript + chat messages for context
        transcript_context = get_transcript_context()  # all finalized speech
        recent_messages = "\n".join(self.messages[-5:])  # recent chat lines

        # Combine incremental transcript + recent chat
        selected_model = self.model_selector.currentText()
        full_query = {
            "prompt": f"{transcript_context}\n{recent_messages}\nUser: {user_text}",
            "model": selected_model  # <-- Pass model name
        }

        # Add user message to chat panel
        self.messages.append(f"User: {user_text}")
        self.messages.append("Halo: ")  # placeholder

        self.current_reply_index = len(self.messages) - 1
        self.reply_text = ""

        # Update UI immediately
        self.update_chat_display()
        self._protect_window()

        # Start worker
        self.worker = LLMWorker(full_query)
        self.worker.token_received.connect(self.on_token_received)
        self.worker.finished.connect(self.on_reply_finished)
        self.worker.start()

        self.input.clear()



    def on_token_received(self, token):
            self.reply_text += token
            self.messages[self.current_reply_index] = f"Halo: {self.reply_text}"
            self.update_chat_display()  # refresh QTextEdit

    def on_reply_finished(self):
            print("✅ Reply finished streaming.")

    def update_chat_display(self):
        # Display messages from the Python list in the QTextEdit
        self.chat_box.setPlainText("\n".join(self.messages))

        # Move cursor to the end so new text is always visible
        cursor = self.chat_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_box.setTextCursor(cursor)

    def copy_last_code_block(self):
        """
        Search the last code block in self.reply_text (or messages) and copy it to clipboard.
        """
        # Search messages in reverse for a code block
        for msg in reversed(self.messages):
            code_match = re.search(r"```(.*?)```", msg, re.DOTALL)
            if code_match:
                code_text = code_match.group(1).strip()
                clipboard = QApplication.clipboard()
                clipboard.setText(code_text)
                print("✅ Code copied to clipboard")
                return

        print("⚠️ No code block found to copy")


    def use_suggestion(self):
        text = self.suggestion_label.text()
        self.input.setText(text)
        self.send_message()

    def stop_current_reply(self):
    # Stop the running LLaMA worker thread
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()  # ensures thread fully stops

        # Replace partial AI reply with [Stopped] message
        if hasattr(self, "current_reply_index"):
            self.messages[self.current_reply_index] = "Halo: [Stopped]"
            self.reply_text = ""
            self.update_chat_display()

        # Remove unfinished AI placeholder at the end, so next query is fresh
        if len(self.messages) > 0 and self.messages[-1] == "Halo: ":
            self.messages.pop()



# ----------------- Floating Overlay -----------------
class FloatingOverlay(QWidget):
    update_transcript_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(1200, 50, 550, 70)
        self.update_transcript_signal.connect(self._update_transcript_ui)

        self.drag_position = None
        
        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background: rgba(17,17,17,180);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,50);
            }
        """)
        self.container.setGeometry(0, 0, 550, 70)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Logo
        self.logo = QLabel("H")
        self.logo.setFixedSize(32, 32)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.logo)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #10b981; border-radius: 6px;")
        layout.addWidget(self.status_dot)

        # Icon paths
        icon_paths = {
            'mic': os.path.join("halo", "ui", "assets", "listen.svg"),
            'chat': os.path.join("halo", "ui", "assets", "Question.svg"),
            'hide': os.path.join("halo", "ui", "assets", "incognito.svg"),
            'stop': os.path.join("halo", "ui", "assets", "stop.svg")
        }

        # Listen button
        self.listen_btn = QPushButton("Listen")
        self.listen_btn.setStyleSheet(self.button_style())
        self.listen_btn.setIcon(QIcon(icon_paths['mic']))
        self.listen_btn.setIconSize(QtCore.QSize(20, 20))
        self.listen_btn.clicked.connect(self.toggle_listening_state)
        layout.addWidget(self.listen_btn)

        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(self.button_style())
        self.stop_btn.setIcon(QIcon(icon_paths['stop']))
        self.stop_btn.setIconSize(QtCore.QSize(20, 20))
        self.stop_btn.clicked.connect(self.stop_all)
        self.stop_btn.hide()
        layout.addWidget(self.stop_btn)

        # Ask Question button
        self.chat_btn = QPushButton("Ask Question")
        self.chat_btn.setStyleSheet(self.button_style())
        self.chat_btn.setIcon(QIcon(icon_paths['chat']))
        self.chat_btn.setIconSize(QtCore.QSize(20, 20))
        self.chat_btn.clicked.connect(self.toggle_chat)
        layout.addWidget(self.chat_btn)

        # Stop LLaMA button
        self.stop_llama_btn = QPushButton("Stop AI")
        self.stop_llama_btn.setStyleSheet(self.button_style())
        self.stop_llama_btn.setFixedHeight(30)
        self.stop_llama_btn.clicked.connect(self.stop_llama)
        layout.addWidget(self.stop_llama_btn)
        self._protect_window()

        self.container.setLayout(layout)


        # Chat panel
        self.chat_panel = ChatPanel()
        self.chat_panel.hide()

        # Status and timers
        self.is_listening = False
        self.is_paused = False
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_dot)
        self.blink_state = False


        # ----------------- Transcript panel -----------------
        self.transcript_panel = QTextEdit()
        self.transcript_panel.setReadOnly(True)
        self.transcript_panel.setStyleSheet("""
            QTextEdit {
                background: rgba(30,30,30,220);
                color: #ffffff;
                border-radius: 12px;
            }
        """)
        self.transcript_panel.setGeometry(10, 90, 330, 200)  # adjust size/position
        self.transcript_panel.hide()  # hide by default

        # Button to toggle transcript panel
        self.transcript_btn = QPushButton("Show Transcript")
        self.transcript_btn.setStyleSheet(self.button_style())
        self.transcript_btn.setFixedHeight(30)
        self.transcript_btn.clicked.connect(self.toggle_transcript_panel)
        layout.addWidget(self.transcript_btn)
        

    def stop_llama(self):
        if self.chat_panel:
            self.chat_panel.stop_current_reply()

    def _protect_window(self):
        """
        Prevent overlay from appearing in screen capture/screenshot.
        Works on Windows 10+.
        """
        try:
            hwnd = int(self.winId())  # Get native window handle
            user32 = ctypes.windll.user32

            # Constants
            WDA_NONE = 0x0
            WDA_MONITOR = 0x1
            WDA_EXCLUDEFROMCAPTURE = 0x11  # Best option (Win 10 2004+)

            # Try strongest protection first
            if not user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
                # Fallback for slightly older Windows
                user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)

            print("✅ Overlay protected from screenshots & screen share.")

        except Exception as e:
            print(f"⚠️ Could not protect overlay: {e}")

    def _update_transcript_ui(self, text):
    # Send transcript to the new panel, not chat_panel
        self.transcript_panel.setPlainText(text)
        self.transcript_panel.verticalScrollBar().setValue(
            self.transcript_panel.verticalScrollBar().maximum()
        )


    def _record_loop(self):
        """
        Consume results from record_continuous().

        - result is a dict: {"type": "partial" | "final", "text": str}
        - On partial: show live line appended to current final transcript (not saved).
        - On final: update UI with saved transcript (pipeline already saved it).
        """
        for result in record_continuous():
            if self._stop_event.is_set():
                # ensure the mic stream is shut down inside the generator too
                stop_streaming()
                break

            if self.is_paused:
                QtCore.QThread.msleep(100)
                continue

            # Backward compatibility if anything yields plain strings
            if not isinstance(result, dict):
                text = str(result).strip()
                if text:
                    full_transcript = get_transcript_context()  # only finals
                    # show finals + the new line (treated as final)
                    combined = (full_transcript + ("\n" if full_transcript else "") + text).strip()
                    self.update_transcript_signal.emit(combined)
                continue

            text = result.get("text", "").strip()
            if not text:
                continue

            if result.get("type") == "partial":
                # Show current saved finals + a live partial preview line
                finals = get_transcript_context()  # contains only finalized text
                live_view = (finals + ("\n" if finals else "") + f"[…] {text}").strip()
                self.update_transcript_signal.emit(live_view)
            else:
                # Final result: pipeline already saved it; re-render from cache
                finals = get_transcript_context()
                self.update_transcript_signal.emit(finals)

    def button_style(self):
        return """
            QPushButton {
                background: rgba(255,255,255,30);
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 12px;
                padding: 6px 10px;
            }
            QPushButton:hover { background: rgba(255,255,255,50); }
        """

    # Movable overlay
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_position and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    # Listen / Pause / Resume
    def toggle_listening_state(self):
        if not self.is_listening:
            start_new_session()  # start fresh transcript
            self.is_listening = True
            self.is_paused = False
            self.listen_btn.setText("Pause")
            self.stop_btn.show()
            self._stop_event = threading.Event()

            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.recording_thread.start()
            self.blink_timer.start(500)
        else:
            # Toggle pause/resume
            self.is_paused = not self.is_paused
            self.listen_btn.setText("Resume" if self.is_paused else "Pause")
            if self.is_paused:
                self.blink_timer.stop()
            else:
                self.blink_timer.start(500)

    def stop_all(self):
        # Stop recording
        if self.is_listening:
            self.is_listening = False
            self.is_paused = False
            self.listen_btn.setText("Listen")
            self.stop_btn.hide()
            self.blink_timer.stop()
            self.status_dot.setStyleSheet("background-color: #10b981; border-radius: 6px;")
            if hasattr(self, "_stop_event"):
                self._stop_event.set()
            if hasattr(self, "recording_thread") and self.recording_thread.is_alive():
                self.recording_thread.join()

        # Stop any ongoing LLaMA response
        if self.chat_panel:
            self.chat_panel.stop_current_reply()  # <-- calls updated method



    def blink_dot(self):
        self.blink_state = not self.blink_state
        color = "#ef4444" if self.blink_state else "#10b981"
        self.status_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")

    def toggle_transcript_panel(self):
        if self.transcript_panel.isVisible():
            self.transcript_panel.hide()
            self.transcript_btn.setText("Show Transcript")
        else:
            self.transcript_panel.show()
            self.transcript_btn.setText("Hide Transcript")

    def stop_llama(self):
        if self.chat_panel:
            self.chat_panel.stop_current_reply()



    # Chat toggle
    def toggle_chat(self):
        if self.chat_panel.isVisible():
            self.chat_panel.hide()
        else:
            self.chat_panel.show()

    def hide_overlay(self):
        self.hide()

    def show_overlay(self):
        self.show()

    def append_transcript(self, text):
        if not self.is_paused:
            self.chat_panel.messages.append(f"Transcript: {text}")

# # ----------------- Run App -----------------
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     overlay = FloatingOverlay()
#     overlay.show()
#     sys.exit(app.exec())
