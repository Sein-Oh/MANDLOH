import py_cui

class App:
    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        self.root.add_key_command(py_cui.keys.KEY_C_LOWER, self.key_event)


        self.menu = self.root.add_scroll_menu("MONITOR", 0, 0)
        self.menu.add_item_list(["Item1", "Item2", "Item3"])
        self.menu.add_key_command(py_cui.keys.KEY_ENTER, self.key_event)
        self.menu.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, self.show_text_box)
        self.menu.set_selected_color(py_cui.WHITE_ON_BLUE)
        self.menu.set_focus_border_color(5)


        self.box = self.root.add_text_block("EDITOR", 0, 1)
        self.box.set_selected_color(py_cui.WHITE_ON_BLUE)
        self.box.set_focus_border_color(5)

        self.info = self.root.add_label("CHANGE", 1, 0, column_span=2)

    def key_event(self):
        self.info.set_title(self.menu.get())
        self.root.set_selected_widget(1)

    def mouse_event(self, x, y):
        self.info.set_title(self.menu.get())
        self.menu.add_item_list(["Item4"])

    def set_title(self, title):
        self.info.set_title(title)

    def show_text_box(self):
        self.root.show_text_box_popup("Enter a new value.", lambda x:self.change_list(self.menu, x))

    def change_list(self, widget, value):
        items = widget.get_item_list()
        items[items.index(widget.get())] = value
        widget.clear()
        widget.add_item_list(items)


root = py_cui.PyCUI(2,2)
App(root)
root.start()
