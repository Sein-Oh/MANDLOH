from textual.app import App
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static, Button, TextLog, Checkbox, Input
from textual.widget import Widget
from StringProgressBar import progressBar

class TitleLog(Static):
    def compose(self):
        yield Static(self.renderable, classes="title")
        yield TextLog()
        
class Monitor(Static):
    def compose(self):
        yield Static(self.renderable, classes="title")
        yield Static("")
        self.hp = Static()
        self.mp = Static()
        yield self.hp
        yield self.mp
        yield Static("")

    def on_mount(self):
        self.update_value(100, 100)

    def update_value(self, hp, mp):
        self.hp.update(f"  HP [{str(hp).rjust(3)}%] [[red]{progressBar.filledBar(100, hp, 30, ' ', '=')[0]}[/red]]")
        self.mp.update(f"  MP [{str(mp).rjust(3)}%] [[blue]{progressBar.filledBar(100, mp, 30, ' ', '=')[0]}[/blue]]")

class Check(Static):
    def compose(self):
        yield Static(self.renderable, classes="label")
        yield Checkbox()

class MyApp(App):
    CSS_PATH = "app.css"

    def compose(self):
        yield Horizontal(Monitor("  STATUS"), TitleLog("  MESSAGE") , classes="box")
        yield Button("TEST", id="test")
        yield Check("USE")


    # def on_click(self, event):
    #     self.query_one("TitleLog > TextLog").write(event)

    def on_button_pressed(self, event):
        # self.query_one("TitleLog > TextLog").write(event)
        if event.button.id == "test":
            self.query_one(Monitor).update_value(90, 90)

app = MyApp()
app.run()
