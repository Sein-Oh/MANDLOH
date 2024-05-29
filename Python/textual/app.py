from textual.app import App
from textual.widgets import Header, Footer, Switch, Static, Button, Log, Input
from textual.containers import Horizontal
import win32gui

# Get window handle
app_hwnd = win32gui.GetForegroundWindow()

# Set window size and position(Windows only. Right side)
win32gui.MoveWindow(app_hwnd, 0, 0, 400, 600, True)

class MyInput(Static):
    def compose(self):
        yield Horizontal(
            Static(self.renderable),
            Input()
        )


class MyButton(Static):
    def compose(self):
        yield Horizontal(
            Button(self.renderable, variant="success"),
            Static("Text\nText2\nText3")
        )

class MyApp(App):
    def compose(self):
        yield MyButton("Timer 1")
        yield MyButton("Timer 2")
        yield MyButton("Timer 3")
        yield MyInput("MYINPUT")
        yield Log(id="log")

    def on_button_pressed(self, event):
        variant = event.button.variant
        event.button.variant = "success" if variant == "default" else "default"
        self.query_one("#log").write_line("Hello world")


    def on_ready(self):
        self.query_one("#log").write_line("Hello world")



app = MyApp(css_path="app.tcss")
app.run()
