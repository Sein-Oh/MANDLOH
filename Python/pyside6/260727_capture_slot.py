import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QScrollArea, QSizePolicy, QPushButton
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer
app = QApplication(sys.argv)

import cv2
import dxcam
import numpy as np


class SlotWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.state = "stop"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2,1,2,1)
        layout.setSpacing(1)

        ### Label
        self.label = QLabel(self.name)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.label)

        ### State buttons
        self.btn_stop = QPushButton("STOP")
        self.btn_idle = QPushButton("IDLE")
        self.btn_run = QPushButton("RUN")

        self.btn_stop.setFixedWidth(40)
        self.btn_idle.setFixedWidth(40)
        self.btn_run.setFixedWidth(40)

        self.btn_stop.clicked.connect(lambda: self.set_state("stop"))
        self.btn_idle.clicked.connect(lambda: self.set_state("idle"))
        self.btn_run.clicked.connect(lambda: self.set_state("run"))

        self._update_button_styles()

        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_idle)
        layout.addWidget(self.btn_run)

    def _update_button_styles(self):
        norman_style = "font-size: 10px;"
        stop_active = "background-color: #FF4B4B;color: white; font-weight: bold;"
        idle_active = "background-color: #FFA500;color: white; font-weight: bold;"
        run_active = "background-color: #4CAF50;color: white; font-weight: bold;"

        self.btn_stop.setStyleSheet(stop_active if self.state == "stop" else norman_style)
        self.btn_idle.setStyleSheet(idle_active if self.state == "idle" else norman_style)
        self.btn_run.setStyleSheet(run_active if self.state == "run" else norman_style)

    def set_state(self, new_state):
        self.state = new_state
        self._update_button_styles()

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slot UI")
        self.slots = []

        self.preview_width = 320

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(5,5,5,5)

        ### Image preview
        self.image_container = QWidget()
        self.image_container_layout = QVBoxLayout(self.image_container)
        self.image_container_layout.setContentsMargins(0,0,0,0)
        self.image_container_layout.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_container_layout.addWidget(self.image_label)

        ### Menu buttons
        menu_widget = QWidget()
        menu_layout = QHBoxLayout(menu_widget)
        menu_layout.setContentsMargins(0,5,0,0)
        menu_layout.setSpacing(5)

        btn_all_stop = QPushButton("All stop")
        btn_all_stop.clicked.connect(self.all_stop)
        btn_help = QPushButton("Help")
        menu_layout.addWidget(btn_all_stop)
        menu_layout.addWidget(btn_help)

        ### Slot container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_content = QWidget()
        self.file_list_layout = QVBoxLayout(scroll_content)
        self.file_list_layout.setAlignment(Qt.AlignTop)
        self.file_list_layout.setContentsMargins(0,0,0,0)
        self.file_list_layout.setSpacing(2)

        self.scroll.setWidget(scroll_content)

        main_layout.addWidget(self.image_container, 0)
        main_layout.addWidget(menu_widget, 0)
        main_layout.addWidget(self.scroll, 1)

        for i in range(10):
            self.add_slot(f"{i} - Slot")


        self.camera = dxcam.create(output_color="BGR")
        self.camera.start(target_fps=30)

        self.loop_timer = QTimer(self)
        self.loop_timer.timeout.connect(self.loop)
        self.loop_timer.start(500)

        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.update_frame)
        self.capture_timer.start(100)

        self.setFixedSize(340, 400)
    
    def add_slot(self, name):
        item = SlotWidget(name)
        self.file_list_layout.addWidget(item)
        self.slots.append(item)

    def all_stop(self):
        print("all stop")
        for slot in self.slots:
            slot.set_state("stop")

    def update_frame(self):
        frame = self.camera.get_latest_frame()
        h, w = frame.shape[:2]
        new_h = int(h * (self.preview_width / w))
        preview = cv2.resize(frame, (self.preview_width, new_h))
        rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb.shape
        bytes_per_line = channel * width
        q_img = QImage(rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(q_img)
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())

    def loop(self):
        for slot in self.slots:
            if slot.state != "stop":
                print(slot.state)


if __name__ == "__main__":
    window = MainApp()
    window.show()
    sys.exit(app.exec())
