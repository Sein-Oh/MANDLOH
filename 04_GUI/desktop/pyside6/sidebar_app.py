import os
import sys
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import dxcam
from sidebar import Sidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidebar UI")
        
        # Declare preview dimensions
        self.preview_width = 320
        self.preview_height = 180  # Default initial height (16:9 ratio)
        
        self.setFixedSize(330, 450)  # Adjusted window size to fit preview
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.content_layout = QVBoxLayout(self.central_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        
        self.menu_button = QPushButton("☰")
        self.menu_button.setFixedSize(40, 40)
        
        self.content_layout.addWidget(self.menu_button, alignment=Qt.AlignLeft)
        
        # Live screen capture preview label
        self.preview_label = QLabel("Initializing dxcam...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(self.preview_width, self.preview_height)
        self.content_layout.addWidget(self.preview_label, alignment=Qt.AlignLeft)
        
        self.content_layout.addStretch()
        
        self.sidebar = Sidebar(self.central_widget, width=200, title="MENU")
        self.menu_button.clicked.connect(self.sidebar.toggle)
        
        self.sidebar.add_menu_button("Home", self.on_home)
        self.sidebar.add_menu_button("Settings", self.on_home)
        self.sidebar.add_space()
        self.sidebar.add_menu_button("Exit", self.on_home)
        
        # Initialize dxcam
        try:
            self.cam = dxcam.create(output_color='BGR')
            self.cam.start(target_fps=30)
        except Exception as e:
            print(f"Failed to initialize dxcam: {e}")
            self.preview_label.setText(f"dxcam Init Error: {e}")
            self.cam = None
            
        # Update preview at 30 FPS (~33ms interval)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.timer.start(1000 // 30)

    def update_preview(self):
        if self.cam is None:
            return
        
        frame = self.cam.get_latest_frame()
        if frame is not None:
            h, w = frame.shape[:2]
            if w > 0 and h > 0:
                # Dynamically set preview height based on the frame's aspect ratio and preview_width
                new_height = int(self.preview_width * (h / w))
                if new_height != self.preview_height:
                    self.preview_height = new_height
                    self.preview_label.setFixedSize(self.preview_width, self.preview_height)
                
                # Convert BGR frame from dxcam to QImage and display it
                bytes_per_line = 3 * w
                qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(
                    self.preview_width,
                    self.preview_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        # Stop dxcam thread to ensure clean exit of the process
        if hasattr(self, 'cam') and self.cam is not None:
            try:
                self.cam.stop()
            except Exception as e:
                print(f"Error stopping dxcam: {e}")
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Space):
            self.sidebar.toggle()
        else:
            super().keyPressEvent(event)

    def on_home(self):
        print("HOME")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
