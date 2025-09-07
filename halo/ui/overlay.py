import sys
import os
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QTextEdit, QFrame,
    QVBoxLayout, QHBoxLayout, QSizeGrip
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon , QTextCursor
from halo.core.llm import query_ollama

class LLMWorker(QThread):
    token_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            for token in query_ollama(self.prompt, stream=True):
                self.token_received.emit(token)
            self.finished.emit()
        except Exception as e:
            self.token_received.emit(f"[Error] {str(e)}")
            self.finished.emit()

# ----------------- Clickable QLabel -----------------
class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()  # Custom signal
    def mousePressEvent(self, event):
        self.clicked.emit()

# ----------------- Chat Panel -----------------
class ChatPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
        self.chat_box = QTextEdit()  # UI widget for display
        self.chat_box.setReadOnly(True)
        self.chat_box.setStyleSheet("background: transparent; color: white; border: none;")
        self.chat_box.setText("Halo is ready to assist you\n")
        layout.addWidget(self.chat_box, 1)


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
        send_icon = QIcon(os.path.join("halo", "ui", "assets", "send.svg"))
        self.send_btn.setIcon(send_icon)
        self.send_btn.setIconSize(QtCore.QSize(20,20))
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        # Resize handle
        size_grip = QSizeGrip(self)
        layout.addWidget(size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.container.setLayout(layout)

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

        from halo.core.pipeline import get_transcript_context
        context = get_transcript_context()
        full_query = f"{context}\nUser: {user_text}"

        # add user message
        self.messages.append(f"User: {user_text}")
        self.messages.append("Halo: ")  # placeholder

        self.current_reply_index = len(self.messages) - 1
        self.reply_text = ""

        # update UI immediately
        self.update_chat_display()

        # start worker for streaming
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



    def use_suggestion(self):
        text = self.suggestion_label.text()
        self.input.setText(text)
        self.send_message()

# ----------------- Listener Thread -----------------
from halo.core.pipeline import record_continuous

class ListenerThread(QThread):
    new_text = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        while self._running:
            text = record_continuous()
            if text.strip():
                self.new_text.emit(text)

    def stop(self):
        self._running = False

# ----------------- Floating Overlay -----------------
class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(1200, 50, 350, 70)
        self.drag_position = None

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background: rgba(17,17,17,180);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,50);
            }
        """)
        self.container.setGeometry(0, 0, 350, 70)

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

        # Restore button
        self.restore_btn = QPushButton("H")
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                font-weight: bold;
                border-radius: 12px;
                width: 32px;
                height: 32px;
            }
        """)
        self.restore_btn.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.restore_btn.move(10, 10)
        self.restore_btn.clicked.connect(self.show_overlay)
        self.restore_btn.show()

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
            self.is_listening = True
            self.is_paused = False
            self.listen_btn.setText("Pause")
            self.stop_btn.show()
            self.listener_thread = ListenerThread()
            self.listener_thread.new_text.connect(self.append_transcript)
            self.listener_thread.start()
            self.blink_timer.start(500)
        else:
            if not self.is_paused:
                self.is_paused = True
                self.listen_btn.setText("Resume")
                self.blink_timer.stop()
            else:
                self.is_paused = False
                self.listen_btn.setText("Pause")
                self.blink_timer.start(500)

    def stop_all(self):
        self.is_listening = False
        self.is_paused = False
        self.listen_btn.setText("Listen")
        self.stop_btn.hide()
        self.blink_timer.stop()
        self.status_dot.setStyleSheet("background-color: #10b981; border-radius: 6px;")
        if hasattr(self, "listener_thread"):
            self.listener_thread.stop()
            self.listener_thread.quit()
            self.listener_thread.wait()

    def blink_dot(self):
        self.blink_state = not self.blink_state
        color = "#ef4444" if self.blink_state else "#10b981"
        self.status_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")

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
