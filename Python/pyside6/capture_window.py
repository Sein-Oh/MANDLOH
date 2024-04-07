import sys
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QFile, QIODevice, QTimer
from PySide6.QtGui import QPixmap
import dxcam
import qimage2ndarray
import cv2

class MainWindow:
    def __init__(self, window):
        self.window = window
        self.window.pushButton.clicked.connect(self.start_click)
        self.window.pushButton_2.clicked.connect(self.stop_click)

        self.camera = dxcam.create(output_color="BGR")
        self.camera.start(target_fps=10)

        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.display_video_stream)

    def show(self):
        self.window.show()

    def start_click(self):
        self.window.textEdit.append("Hello")
        self.timer.start()

    def stop_click(self):
        self.timer.stop()

    def display_video_stream(self):
        frame = self.camera.get_latest_frame()
        frame = cv2.resize(frame, dsize=(320,240), interpolation=cv2.INTER_AREA)
        image = qimage2ndarray.array2qimage(frame)
        self.window.label.setPixmap(QPixmap.fromImage(image))



if __name__ == "__main__":
    loader = QUiLoader()
    app = QApplication(sys.argv)
    window = loader.load("form.ui", None)
    main_window = MainWindow(window)
    main_window.show()
    sys.exit(app.exec())
