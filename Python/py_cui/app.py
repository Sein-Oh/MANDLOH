import py_cui

class App:
    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        # self.root.set_widget_border_characters(" ", " ", " ", " ", "〓", "║")
        self.root.toggle_unicode_borders()


        self.lbl = self.root.add_label("MANDLOH CUI TEST", 0, 0, column_span=4)
        opts = ["Item1", "Item2", "Item3", "Item4"]
        self.menu = self.root.add_scroll_menu("MENU", 1, 0, row_span=4)
        self.menu_pos = self.menu.get_absolute_start_pos()
        self.menu.add_item_list(opts)
        self.menu.set_selected_color(15)
        self.menu.add_mouse_command(py_cui.keys.LEFT_MOUSE_CLICK, self.print_left_press_with_coords)

        self.btn = self.root.add_button("BUTTON", 5, 0, command=self.btn)
        self.input = self.root.add_text_box("HELLO", 6, 0)

        root.add_key_command(py_cui.keys.KEY_A_LOWER, self.test)

    def test(self):
        self.lbl.set_title(str(self.root.get_widgets()))

    def clear_text_field(self):
        self.text_field.clear()
    
    def print_left_press_with_coords(self, x, y):
        selected_row = y - self.menu_pos[1]
        self.lbl.set_title(f"selected row : {selected_row}")

    def btn(self):
        self.input.set_selected(True)


root = py_cui.PyCUI(9,4)
App(root)
root.start()
