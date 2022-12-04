import py_cui
import art

class App:
    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        # self.root.set_widget_border_characters(" ", " ", " ", " ", "〓", "║")
        # self.root.toggle_unicode_borders()
        self.figlet = self.root.add_block_label(art.text2art("MANDLOH", "rectangles"), 0, 0, row_span=2, column_span=4)
        self.figlet.set_selectable(False)
        self.figlet.set_color(5)

        self.info = self.root.add_text_block("Monitor", 2, 0, row_span=2, column_span=1)
        self.info.set_text("HP:\nMP:")

        # self.lbl = self.root.add_label("MANDLOH CUI TEST", 0, 0, column_span=4)
        """
        opts = ["Item1", "Item2", "Item3", "Item4"]
        self.menu = self.root.add_scroll_menu("MENU", 1, 0, row_span=3)
        self.menu_pos = self.menu.get_absolute_start_pos()
        self.menu.add_item_list(opts)
        self.menu.set_selected_color(15)
        self.menu.set_focus_border_color(5)
        self.menu.add_key_command(py_cui.keys.KEY_ENTER, self.test)
        self.menu.add_mouse_command(py_cui.keys.LEFT_MOUSE_CLICK, self.menu_mouse_handle)

        self.btn = self.root.add_button("BUTTON", 4, 0)
        self.input = self.root.add_text_box("TEXT BOX", 5, 0, initial_text="HELLO")
        self.input.set_selected_color(5)
        self.input.add_mouse_command(py_cui.keys.LEFT_MOUSE_CLICK, lambda: self.root.move_focus(self.input))
        self.root.add_key_command(py_cui.keys.KEY_A_LOWER, self.test)
        """

    def test(self):
        selected = self.menu.get_selected_item_index()
        self.lbl.set_title(f"Selected item : {selected}")
    
    def menu_mouse_handle(self, x, y):
        self.root.move_focus(self.menu)
        selected_row = y - self.menu_pos[1] - 1
        self.lbl.set_title(f"Selected item : {selected_row}")
        

root = py_cui.PyCUI(8,4)
App(root)
root.start()
