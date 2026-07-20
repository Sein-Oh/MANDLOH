
from PySide6.QtWidgets import (
    QFrame, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QScrollArea
)
from PySide6.QtCore import Qt, QRect, QEasingCurve, QPropertyAnimation


class Sidebar(QFrame):
    """Animated sidebar widget."""

    def __init__(self, parent, width=220, title="MENU"):
        super().__init__(parent)

        self.sidebar_width = width
        self._visible = False

        self.setGeometry(-width, 0, width, parent.height())
        self._build_ui(title)
        self._build_animation()

    def _build_ui(self, title):
        self.setObjectName("sidebar")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)

        label = QLabel(title)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_button")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.toggle)

        header_layout.addWidget(label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.menu_layout = QVBoxLayout(container)
        self.menu_layout.setContentsMargins(8, 8, 8, 8)
        self.menu_layout.setSpacing(4)
        self.menu_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(container)

        root.addWidget(header)
        root.addWidget(self.scroll)

        self.setStyleSheet("""
            #sidebar {
                background:#2c3e50;
                border-right:1px solid #1a252f;
            }

            QLabel {
                color:white;
                font-size:18px;
                font-weight:bold;
            }

            QPushButton#close_button {
                background:transparent;
                border:none;
                color:white;
                font-size:16px;
            }

            QPushButton#close_button:hover {
                color:#e74c3c;
            }

            QPushButton[menu="true"] {
                background:#34495e;
                border:none;
                border-radius:6px;
                color:white;
                text-align:left;
                padding:10px;
                font-size:14px;
            }

            QPushButton[menu="true"]:hover {
                background:#4e6a85;
            }

            QScrollArea {
                border:none;
                background:transparent;
            }

            QScrollArea > QWidget > QWidget {
                background:transparent;
            }

            QScrollBar:vertical {
                width:8px;
                border:none;
                background:#2c3e50;
            }

            QScrollBar::handle:vertical {
                background:#4e6a85;
                border-radius:4px;
                min-height:20px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0px;
            }
        """)

    def _build_animation(self):
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    def add_menu_button(self, text, callback):
        btn = QPushButton(text)
        # ObjectName 대신 Dynamic Property 사용
        btn.setProperty("menu", True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)

        # Dynamic Property 변경 시 스타일 재적용
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        self.menu_layout.addWidget(btn)
        return btn

    def toggle(self):
        x = 0 if not self._visible else -self.sidebar_width

        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(
            QRect(x, 0, self.sidebar_width, self.parent().height())
        )
        self.animation.start()

        self._visible = not self._visible

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._visible:
            self.setGeometry(
                0, 0, self.sidebar_width, self.parent().height()
            )
