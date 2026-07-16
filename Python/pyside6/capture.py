import sys
# 1. Qt 핵심 모듈을 먼저 임포트합니다.
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QTextEdit, QFrame
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap

# 2. 다른 라이브러리가 DPI 설정을 선점하기 전에 QApplication을 가장 먼저 생성합니다.
app = QApplication(sys.argv)

# 3. 그 다음 무거운 외부 라이브러리들을 임포트합니다.
import dxcam
import qimage2ndarray
import cv2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("MainWindow")
        self.resize(330, 434)

        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self.label = QLabel(self.centralwidget)
        self.label.setGeometry(5, 5, 320, 240)
        self.label.setFrameShape(QFrame.Box)

        self.pushButton = QPushButton("Play", self.centralwidget)
        self.pushButton.setGeometry(10, 250, 151, 31)
        self.pushButton.clicked.connect(self.start_click)

        self.pushButton_2 = QPushButton("Stop", self.centralwidget)
        self.pushButton_2.setGeometry(170, 250, 151, 31)
        self.pushButton_2.clicked.connect(self.stop_click)

        self.textEdit = QTextEdit(self.centralwidget)
        self.textEdit.setGeometry(10, 290, 311, 121)
        self.textEdit.setReadOnly(True)

        self.camera = dxcam.create(output_color="BGR")
        self.camera.start(target_fps=10)

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.display_video_stream)

    def start_click(self):
        self.textEdit.append("Hello")
        self.timer.start()

    def stop_click(self):
        self.timer.stop()

    def display_video_stream(self):
        frame = self.camera.get_latest_frame()
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(rgb_frame, dsize=(320, 240), interpolation=cv2.INTER_AREA)
            image = qimage2ndarray.array2qimage(resized_frame)
            self.label.setPixmap(QPixmap.fromImage(image))

if __name__ == "__main__":
    # app 생성을 최상단으로 옮겼으므로 여기서는 윈도우만 띄워줍니다.
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
