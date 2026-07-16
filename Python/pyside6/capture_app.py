# app.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QTextEdit, QFrame
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

# DPI 경고 방지를 위해 QApplication 최상단 선언
app = QApplication(sys.argv)

import cv2
import qimage2ndarray
# 제작한 커스텀 모듈 모듈 불러오기
from ps6_capture import Ps6Capture 

class VideoThread(QThread):
    frame_received = Signal(QImage)
    status_logged = Signal(str)

    def __init__(self, mode, use_requests=False, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.use_requests = use_requests
        self.running = False

    def run(self):
        self.running = True
        # 요청하신 규격대로 객체 생성
        capture = Ps6Capture(self.mode, requests=self.use_requests)

        if not capture.isOpened():
            self.status_logged.emit("스트림 소스를 열 수 없습니다.")
            return

        self.status_logged.emit("스트리밍 시작됨")

        while self.running:
            ret, frame = capture.read()
            if ret and frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(rgb_frame, dsize=(320, 240), interpolation=cv2.INTER_AREA)
                qimg = qimage2ndarray.array2qimage(resized)
                self.frame_received.emit(qimg)
            else:
                self.status_logged.emit("프레임을 읽지 못했거나 스트림이 종료되었습니다.")
                break

        capture.release()
        self.status_logged.emit("스트리밍 정지됨")

    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Video Player")
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

        self.video_thread = None

    def start_click(self):
        if self.video_thread and self.video_thread.isRunning():
            return

        # -----------------------------------------------------------------
        # 설정 예시 조절 영역
        # -----------------------------------------------------------------
        # 예시 A: Termux 환경에서 IP 캠 주소 연결할 때
        target_mode = "http://127.0.0.1:8080/"
        use_requests = False
        
        # 예시 B: 일반 PC 환경에서 0번 내장 웹캠 연결할 때
        # target_mode = 0
        # use_requests = False
        # -----------------------------------------------------------------

        self.video_thread = VideoThread(target_mode, use_requests=use_requests)
        self.video_thread.frame_received.connect(self.update_label)
        self.video_thread.status_logged.connect(self.log_message)
        self.video_thread.start()

    def stop_click(self):
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()

    @Slot(QImage)
    def update_label(self, qimg):
        self.label.setPixmap(QPixmap.fromImage(qimg))

    @Slot(str)
    def log_message(self, message):
        self.textEdit.append(message)

    def closeEvent(self, event):
        self.stop_click()
        event.accept()

if __name__ == "__main__":
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())