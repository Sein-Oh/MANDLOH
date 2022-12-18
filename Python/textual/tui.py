from textual.app import App
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static, Button
from textual.widget import Widget
from StringProgressBar import progressBar

class MyApp(App):
    DEFAULT_CSS = """
    #monitor {
        background: $boost;
        width: auto;
    }
    """
    def compose(self):
        yield Horizontal(Static(id="monitor"), Static("SELECT", classes="select"))

    def on_mount(self):
        self.update_monitor(30, 80)

    def make_progress(self, value):
        return progressBar.filledBar(100, value, 30, " ", "=")[0]

    def update_monitor(self, hp, mp):
        hpBar = f"HP [{str(hp).rjust(3)}%] [[red]{self.make_progress(hp)}[/red]]"
        mpBar = f"MP [{str(mp).rjust(3)}%] [[blue]{self.make_progress(mp)}[/blue]]"
        self.query_one("#monitor").update(f"{hpBar}\n{mpBar}")

MyApp().run()
