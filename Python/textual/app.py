from textual.app import App
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static, Button, TextLog, Label
from textual.widget import Widget
from StringProgressBar import progressBar

class TitleLog(Static):
    def compose(self):
        yield Static(self.renderable, classes="title")
        yield TextLog()
        
class Monitor(Static):
    def compose(self):
        yield Static(self.renderable, classes="title")
        yield Static(id="hp")
        yield Static(id="mp")
        yield Static("")

class BoolLabel(Widget):
    title = reactive("TITLE")
    value = reactive(False)
    
    def render(self):
        return f"{self.title.rjust(8)}:{self.value}"
    
    def on_click(self):
        self.value = not self.value


class MyApp(App):
    CSS_PATH = "app.css"

    def compose(self):
        yield Horizontal(Monitor("STATUS"), TitleLog("MESSAGE") , classes="box")
        yield Button("TEST")

    def on_mount(self):
        self.update_monitor(30, 80)

    def on_click(self, event):
        self.query_one("TitleLog > TextLog").write(event)

    def on_button_pressed(self, event):
        self.query_one("TitleLog > TextLog").write(event)
        self.update_monitor(90, 90)

    def make_progress(self, value):
        return progressBar.filledBar(100, value, 30, " ", "=")[0]

    def update_monitor(self, hp, mp):
        hpBar = f"HP [{str(hp).rjust(3)}%] [[red]{self.make_progress(hp)}[/red]]"
        mpBar = f"MP [{str(mp).rjust(3)}%] [[blue]{self.make_progress(mp)}[/blue]]"
        self.query_one("Monitor > #hp").update(hpBar)
        self.query_one("Monitor > #mp").update(mpBar)


MyApp().run()
