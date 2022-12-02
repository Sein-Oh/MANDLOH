from rich.markdown import Markdown
from textual.app import App
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static
import art


WIDGETS_MD = """

Textual widgets are powerful interactive components.

Build your own or use the builtin widgets.

- **Input** Text / Password input.
- **Button** Clickable button with a number of styles.
- **Checkbox** A checkbox to toggle between states.
- **DataTable** A spreadsheet-like widget for navigating data. Cells may contain text or Rich renderables.
- **TreeControl** An generic tree with expandable nodes.
- **DirectoryTree** A tree of file and folders.
- *... many more planned ...*

"""


class Body(Container):
    pass


class SectionTitle(Static):
    pass

class Section(Container):
    pass


class Column(Container):
    pass

class TextContent(Static):
    pass


class QuickAccess(Container):
    pass

class Label(Static):
    text = reactive(0)

    def on_mount(self):
        self.update_timer = self.set_interval(1, self.update_value, pause=True)

    def render(self):
        return str(self.text)

    def update_value(self):
        self.text += 1

    def start(self):
        self.update_timer.resume()

    def stop(self):
        self.update_timer.pause()



class LocationLink(Static):
    def __init__(self, label: str, reveal: str) -> None:
        super().__init__(label)
        self.reveal = reveal

    def on_click(self) -> None:
        self.app.query_one(self.reveal).scroll_visible(top=True, duration=0.5)


class SubTitle(Static):
    pass

class DemoApp(App):
    CSS_PATH = "app.css"
    TITLE = "Textual Demo"

    def compose(self):
        yield Header(show_clock=True)
        yield Container(
            Horizontal(
                Button.success("RUN", id="run"),
                Button.error("STOP", id="stop"),
                Button("ART", id="art"),
                Label()),
            id="main"
        )
        yield Container(
            Body(
                QuickAccess(
                    LocationLink("Widgets", ".location-widgets"),
                    LocationLink("Rich content", ".location-rich"),
                    LocationLink("CSS", ".location-css"),
                ),
                Column(
                    Section(
                        SectionTitle("Widgets"),
                        TextContent(Markdown(WIDGETS_MD)),
                    ),
                    classes="location-widgets location-first",
                ),
                Column(
                    Section(
                        SectionTitle("Rich"),
                        SubTitle("Pretty Printed data (try resizing the terminal)"),
                    ),
                    classes="location-rich",
                ),
                Column(
                    Section(
                        SectionTitle("CSS"),
                    ),
                    classes="location-css",
                ),
            ),
        )
        yield Footer()

    def on_button_pressed(self, event):
        btn_id = event.button.id
        if btn_id == "run":
            self.query_one(Label).start()
        elif btn_id == "stop":
            self.query_one(Label).stop()
        elif btn_id == "art":
            self.query_one(Label).text = art.text2art("BTN")

DemoApp().run()
