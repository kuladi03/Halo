from PyQt6.QtWidgets import QApplication
from halo.ui.overlay import FloatingOverlay
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = FloatingOverlay()
    overlay.show()
    sys.exit(app.exec())
