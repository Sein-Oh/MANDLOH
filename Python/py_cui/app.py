import py_cui
import threading
from StringProgressBar import progressBar

"""
button.set_color(int) --> border
0 : white
1 : white
2 : yellow
3 : red
4 : sky
5 : purple
6 : green
7 : blue
"""

class App:
    def __init__(self, root: py_cui.PyCUI):
        self.running = False
        self.root = root
        self.root.set_title("Lineage-W by MANDLOH")
        self.root.set_refresh_timeout(1)
        # self.root.set_widget_border_characters(" ", " ", " ", " ", "-", "|")
        # self.root.toggle_unicode_borders()        

        self.hp = self.root.add_label(self.progress_bar("HP",100,100,30), 0, 1, column_span=2)
        self.hp.add_text_color_rule("=", py_cui.WHITE_ON_RED, "contains", match_type='regex')

        self.mp = self.root.add_label(self.progress_bar("MP",100,50,30), 0, 3, column_span=2)
        self.mp.add_text_color_rule("=", py_cui.WHITE_ON_BLUE, "contains", match_type='regex')

        self.run = self.root.add_button("RUN", 1, 1, command=self.btn_run)
        self.run.set_color(1)
        self.stop = self.root.add_button("STOP", 1, 2, command=self.btn_stop)
        self.stop.set_color(6)
        self.key = ["USE", "HP_MIN", "HP_MAX", "MP_MIN", "MP_MAX", "KEY", "COUNT", "DELAY", "COOLTIME", "REPEAT"]
        
        self.slot1 = self.root.add_scroll_menu("SLOT1", 4, 0, row_span=4)
        self.slot1_item = list(map(lambda x: x.ljust(9)+":", self.key))
        self.slot1.add_item_list(self.slot1_item)

        self.slot2 = self.root.add_scroll_menu("SLOT2", 4, 1, row_span=4)
        self.slot2_item = list(map(lambda x: x.ljust(9)+":", self.key))
        self.slot2.add_item_list(self.slot2_item)

        self.slot3 = self.root.add_scroll_menu("SLOT3", 4, 2, row_span=4)
        self.slot3_item = list(map(lambda x: x.ljust(9)+":", self.key))
        self.slot3.add_item_list(self.slot3_item)

        self.slot4 = self.root.add_scroll_menu("SLOT4", 4, 3, row_span=4)
        self.slot4_item = list(map(lambda x: x.ljust(9)+":", self.key))
        self.slot4.add_item_list(self.slot4_item)

        # self.info = self.root.add_label("EMPTY", 7, 0)

    def btn_run(self):
        self.run.set_color(6)
        self.stop.set_color(1)
        self.running = True

    def btn_stop(self):
        self.run.set_color(1)
        self.stop.set_color(3)
        self.running = False

    def btn_toggle(self, widget, value=None):
        widget.value = not widget.value
        widget.set_color(6 if widget.value else 1)

    def make_lbl_toggle(self, widget):
        widget.value = False
        widget.set_color(py_cui.BLACK_ON_WHITE)

    def lbl_toggle(self, widget, value=None):
        widget.value = not widget.value
        widget.set_color(py_cui.BLACK_ON_GREEN if widget.value else py_cui.BLACK_ON_WHITE)

    def progress_bar(self, title, total, current, size):
        bar, value = progressBar.filledBar(total, current, size, "-", "=")
        return f"{title} {bar} {str(int(float(value))).rjust(3)}%"
        

root = py_cui.PyCUI(8,6)
App(root)
root.start()
