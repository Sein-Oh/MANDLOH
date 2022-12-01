from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult, App
from textual.widgets import Static, Checkbox, Button, DataTable

class MyApp(App):
    CSS_PATH = "app.css"
    def compose(self):
        yield Horizontal(
            Vertical(
                Static(renderable="Hello1\nHello2\nHello3", id="info"),
                classes="container"
            ),
            Horizontal(
                Static("RUN: ", classes="label"), Checkbox(id="check"), classes="container"
            ), classes="container"
        )
        yield Button("TEST")
        yield DataTable()
        yield Static("TABLE", id="table")

    def on_mount(self):
        table = self.query_one(DataTable)
        # table.show_header = False
        table.add_columns("Name", "Age")
        for name, age in [("Alice", 23), ("Bob", 32), ("Charlie", 28)]:
            table.add_row(name, str(age))

    def on_datatable_pressed(self,event):
        self.query_one("#table").update(renderable=str(event))

    def on_key(self, event):
        self.query_one("#info").update(renderable=str(event))

    def on_mouse_move(self, event):
        # self.query_one("#info").update(renderable=str(event))
        self.screen.query_one(TextLog).write(event)


    def on_button_pressed(self, event):
        self.query_one("#info").update(renderable=str(event))

    def on_checkbox_changed(self, event):
        self.query_one("#info").update(renderable=str(event))




MyApp().run()
