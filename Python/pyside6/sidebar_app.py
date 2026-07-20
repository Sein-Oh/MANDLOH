import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from sidebar import Sidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidebar UI")
        self.setFixedSize(500, 400)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.content_layout = QVBoxLayout(self.central_widget)
        
        self.menu_button = QPushButton("☰")
        self.menu_button.setFixedSize(40, 40)
        
        self.content_layout.addWidget(self.menu_button)
        self.content_layout.addStretch()
        
        self.sidebar = Sidebar(self.central_widget, width=200, title="MENU")
        self.menu_button.clicked.connect(self.sidebar.toggle)
        
        self.sidebar.add_menu_button("Home", self.on_home)
        self.sidebar.add_menu_button("Home", self.on_home)
        self.sidebar.add_menu_button("Home", self.on_home)
        


    def on_home(self):
        print("HOME")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
