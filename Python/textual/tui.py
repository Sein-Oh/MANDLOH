from textual.app import App
from textual.widget import Widget
from textual.widgets import Static, Button, Input, Header, Footer, Checkbox
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from StringProgressBar import progressBar

class StatusMonitor(Static):
    def compose(self):
        yield Vertical(
            Horizontal(Static("HP"), Static(id="hp_bar"), Static("100%", id="hp_val")),
            Horizontal(Static("MP"), Static(id="mp_bar"), Static("100%", id="mp_val")),
            classes="statusPannel"
        )

class MyApp(App):
    CSS_PATH = "tui.css"
    def compose(self):
        yield StatusMonitor()

    def stringBar(self, value):
        return f"[{progressBar.filledBar(100, value, 20, ' ', '=')[0]}]"
    
    def updateHp(self, value):
        self.query_one("#hp_bar").update(self.stringBar(value))
        self.query_one("#hp_val").update(f"[{str(value).rjust(3)}]%")

    def updateMp(self, value):
        self.query_one("#mp_bar").update(self.stringBar(value))
        self.query_one("#mp_val").update(f"[{str(value).rjust(3)}]%")
    
    def on_mount(self):
        self.updateHp(50)
        self.updateMp(100)

MyApp().run()