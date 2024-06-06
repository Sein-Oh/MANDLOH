from textual.app import App
from textual.widgets import Header, Footer, Static, Button, Log
from textual.containers import ScrollableContainer
from textual.binding import Binding
from datetime import datetime
import subprocess
import requests
import os

class MyButton(Static):
    def compose(self):
        yield Button("Run", variant="default")
        yield Static()
    
    def on_button_pressed(self, event):
        event.button.variant = "success" if event.button.variant == "default" else "default"

class MyUI(App):

    BINDINGS =[
        Binding(key="q", action="exit", description="Quit the app"),
        Binding(key="c", action="clear_all", description="All off"),
        Binding(key="a", action="add_slot", description="Add")
        ]

    def compose(self):
        yield Header(show_clock=True)
        yield Log(id="log", name="Message", highlight=True)
        yield ScrollableContainer(id="container")
        yield Footer()

    def on_mount(self):
        self.msg("Input server check...")
        self.input_server = subprocess.Popen(["python", "input_server.py", "--com", "COM10", "--port" , "9000"])
        try:
            res = requests.get("http://127.0.0.1:9000/check", timeout=3)
            if res.text == "OK":
                self.msg("Connected.")
        except:
            self.msg("Failed.")

        self.msg("Stream server check...")
        self.stream_server = subprocess.Popen(["python", "stream_server.py", "--port" ,"8000"])
        try:
            res = requests.get("http://127.0.0.1:8000/check", timeout=3)
            if res.text == "OK":
                self.msg("Connected.")
        except:
            self.msg("Failed.")
        

    def on_button_pressed(self, event):
        self.msg("UPDATE")

    def msg(self, msg):
        clock = datetime.now().time()
        self.query_one("#log").write_line(f"[{clock:%T}] {msg}")

    def action_clear_all(self):
        for btn in self.query("Button"):
            btn.variant = "default"
        self.msg("All off")

    def action_add_slot(self):
        slot = MyButton()
        self.query_one("#container").mount(slot)

    def action_exit(self):
        self.input_server.terminate()
        self.stream_server.terminate()
        os._exit(1)

app = MyUI(css_path="ui.tcss")
app.run()