from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QScrollArea
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect



class Sidebar(QFrame):
    def __init__(self, parent, width=200, title="MENU"):
        super().__init__(parent)
        self.width_val = width
        self.is_visible = False
        
        self.setFixedSize(self.width_val, parent.height())
        self.move(-self.width_val, 0)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2c3e50;
                border-right: 1px solid #1a252f;
            }}
            QLabel {{
                color: white;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton#close_button {{
                background-color: transparent;
                color: white;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton#close_button:hover {{
                color: #e74c3c;
            }}
            QPushButton#menu_item {{
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                text-align: left;
                padding: 12px;
                font-size: 14px;
            }}
            QPushButton#menu_item:hover {{
                background-color: #34495e;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #2c3e50;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #34495e;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #4e6a85;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.title_label = QLabel(title)
        self.close_button = QPushButton("X")
        self.close_button.setObjectName("close_button")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.clicked.connect(self.toggle)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.close_button)
        self.main_layout.addWidget(self.header_widget)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent")
        
        self.button_container = QWidget()
        self.button_container.setStyleSheet("background: transparent")
        self.button_layout = QVBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(5, 5, 5, 5)
        self.button_layout.setSpacing(5)
        self.button_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.button_container)
        self.main_layout.addWidget(self.scroll_area)
        
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        
    def add_menu_button(self, text, callback):
        btn = QPushButton(text)
        btn.setObjectName("menu_item")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        self.button_layout.addWidget(btn)
            
    def toggle(self):
        if not self.is_visible:
            target_rect = QRect(0, 0, self.width_val, self.parent().height())
        else:
            target_rect = QRect(-self.width_val, 0, self.width_val, self.parent().height())
            
        self.animation.stop()
        self.animation.setEndValue(target_rect)
        self.animation.start()
        self.is_visible = not self.is_visible
