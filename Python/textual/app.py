from textual.app import App
from textual.widgets import Header, Footer, Switch, Static, Button, Log
from textual.containers import Horizontal
import win32gui

# Get window handle
app_hwnd = win32gui.GetForegroundWindow()

# Set window size and position(Windows only. Right side)
win32gui.MoveWindow(app_hwnd, 0, 0, 300, 600, True)

class MyButton(Static):
    def compose(self):
        yield Horizontal(
            Button(self.renderable, variant="success"),
            Static("Text", classes="btn_label")
        )

class MyApp(App):
    def compose(self):
        yield Button("Timer 1", id="timer1")
        yield Button("Timer 2", id="timer2", variant="default")
        yield MyButton("Timer 3")
        yield Log(id="log")

    def on_button_pressed(self, event):
        # btn_id = event.button.id
        variant = event.button.variant
        event.button.variant = "success" if variant == "default" else "default"
        self.query_one("#log").write_line("Hello world")


    def on_ready(self):
        self.query_one("#log").write_line("Hello world")



app = MyApp(css_path="app.tcss")
app.run()
