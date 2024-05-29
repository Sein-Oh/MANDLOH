from textual.app import App
from textual.widgets import Header, Footer, Switch, Static, Button, Log, Input
from textual.containers import Horizontal
from textual.binding import Binding
from datetime import datetime

#import win32gui

# Get window handle
#app_hwnd = win32gui.GetForegroundWindow()

# Set window size and position(Windows only. Right side)
#win32gui.MoveWindow(app_hwnd, 0, 0, 400, 600, True)

class MyInput(Static):
    def compose(self):
        yield Horizontal(Static(self.renderable), Input(type="text"))


class MyButton(Static):
    def compose(self):
        yield Horizontal(Button(self.renderable, variant="default"), Static("Text\nText2\nText3"))

class MyApp(App):

    BINDINGS =[
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="r", action="refresh", description="Refresh"),
        Binding(key="c", action="clear_all", description="All off")
    ]

    def compose(self):
        yield Header(show_clock=True)
        yield MyButton("Timer 1")
        yield MyButton("Timer 2")
        yield MyButton("Timer 3")
        yield Log(id="log")
        yield Footer()

    def on_button_pressed(self, event):
        variant = event.button.variant
        event.button.variant = "success" if variant == "default" else "default"
        self.write_log("Button pressed")

    def on_ready(self):
        self.title = "Mandloh app"
        self.write_log("App start.")

    def write_log(self, msg):
        clock = datetime.now().time()
        self.query_one("#log").write_line(f"{clock:%T}: {msg}")

    def action_refresh(self):
        self.write_log("Refresh")

    def action_clear_all(self):
        for btn in self.query("Button"):
            btn.variant = "default"
        self.write_log("All off")

app = MyApp(css_path="app.tcss")
app.run()
