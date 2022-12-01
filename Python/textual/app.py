from rich.markdown import Markdown
from textual.app import App
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

RICH_MD = """

Textual is built on **Rich**, the popular Python library for advanced terminal output.

Add content to your Textual App with Rich *renderables* (this text is written in Markdown and formatted with Rich's Markdown class).

Here are some examples:


"""

CSS_MD = """

Textual uses Cascading Stylesheets (CSS) to create Rich interactive User Interfaces.

- **Easy to learn** - much simpler than browser CSS
- **Live editing** - see your changes without restarting the app!

Here's an example of some CSS used in this app:

"""

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


class LocationLink(Static):
    def __init__(self, label: str, reveal: str) -> None:
        super().__init__(label)
        self.reveal = reveal

    def on_click(self) -> None:
        self.app.query_one(self.reveal).scroll_visible(top=True, duration=0.5)


class SubTitle(Static):
    pass

class DemoApp(App):
    CSS_PATH = "demo.css"
    TITLE = "Textual Demo"

    def compose(self):
        yield Container(
            Header(show_clock=True),
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
                        TextContent(Markdown(RICH_MD)),
                        SubTitle("Pretty Printed data (try resizing the terminal)"),
                    ),
                    classes="location-rich",
                ),
                Column(
                    Section(
                        SectionTitle("CSS"),
                        TextContent(Markdown(CSS_MD)),
                    ),
                    classes="location-css",
                ),
            ),
        )
        yield Footer()

DemoApp().run()
