import py_cui
import art
import threading
from StringProgressBar import progressBar

class App:
    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        self.root.set_title("Lineage-W by MANDLOH")
        self.root.set_refresh_timeout(1)
        self.root.set_widget_border_characters("*", "*", "*", "*", "-", "|")
        # self.root.toggle_unicode_borders()

        # self.figlet = self.root.add_block_label(art.text2art("MANDLOH", "rectangles"), 0, 3, column_span=7, row_span=3)
        # self.figlet.set_selectable(False)
        # self.figlet.set_color(py_cui.MAGENTA_ON_BLACK)

        self.hp = self.root.add_label(self.progress_bar("HP",100,100,20), 0, 0, column_span=3)
        self.hp.set_selectable(False)
        self.hp.add_text_color_rule("=", py_cui.WHITE_ON_RED, "contains", match_type='regex')

        self.mp = self.root.add_label(self.progress_bar("MP",100,99,20), 1, 0, column_span=3)
        self.mp.set_selectable(False)
        self.mp.add_text_color_rule("=", py_cui.WHITE_ON_BLUE, "contains", match_type='regex')

        self.run = self.root.add_label("RUN", 0, 3)
        self.run.add_mouse_command(py_cui.keys.LEFT_MOUSE_CLICK, lambda: self.toggle_event(self.run))
        self.style_to_button(self.run)

        self.help = self.root.add_label("HELP", 0, 4)
        self.help.add_mouse_command(py_cui.keys.LEFT_MOUSE_CLICK, lambda: self.toggle_event(self.help))
        self.style_to_button(self.help)

        self.info = self.root.add_label("EMPTY", 8, 0)
        
        # self.root.add_text_block("Use", 5, 1, column_span=1, row_span=6)
        # self.root.add_text_block("Main", 6, 1, column_span=5, row_span=6)

        # self.menu = self.root.add_scroll_menu("MENU", 4, 0, row_span=2)
        # self.menu.add_item_list(["Slot-1", "Slot-2", "Slot-3", "Slot-4"])
        # self.menu.set_selected_color(15)
        

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
    def style_to_button(self, widget):
        widget.value = False
        widget.set_color(py_cui.BLACK_ON_WHITE)

    def toggle_event(self, widget):
        widget.value = not widget.value
        widget.set_color(py_cui.BLACK_ON_GREEN if widget.value else py_cui.BLACK_ON_WHITE)

    def change_info(self, title, msg):
        self.info.set_title(f"{title}-{msg}")


    def run_evt(self, x, y):
        self.run.set_color(py_cui.BLACK_ON_GREEN if self.run.value else py_cui.BLACK_ON_WHITE)

    def test(self):
        selected = self.menu.get_selected_item_index()
        self.lbl.set_title(f"Selected item : {selected}")
    
    def menu_mouse_handle(self, x, y):
        self.root.move_focus(self.menu)
        selected_row = y - self.menu_pos[1] - 1
        self.lbl.set_title(f"Selected item : {selected_row}")

    def progress_bar(self, title, total, current, size):
        bar, value = progressBar.filledBar(total, current, size, "-", "=")
        return f"{title} {bar} {str(int(float(value))).rjust(3)}%"
        

root = py_cui.PyCUI(24,10)
App(root)
root.start()
