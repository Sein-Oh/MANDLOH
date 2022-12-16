import py_cui
import json
from StringProgressBar import progressBar
import art
import time

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
        # load user_data.json file
        with open("userdata.json", "r") as f:
            self.user_data = json.load(f)

        self.root = root
        self.root.set_title("MADE BY MANDLOH")
        # self.root.toggle_unicode_borders()

        # build widgets
        self.figlet = root.add_block_label(art.text2art("LINEAGE-W", "doom"), 0, 0, row_span=2, column_span=5)
        self.figlet.set_color(py_cui.RED_ON_BLACK)
        self.monitor = self.root.add_text_block("MONITOR", 2, 0, row_span=2, column_span=2)
        self.console = self.root.add_text_block("CONSOLE", 2, 2, row_span=2, column_span=3)
        self.slot_1 = self.root.add_scroll_menu("SLOT-1", 4, 0, row_span=6)
        self.slot_2 = self.root.add_scroll_menu("SLOT-2", 4, 1, row_span=6)
        self.slot_3 = self.root.add_scroll_menu("SLOT-3", 4, 2, row_span=6)
        self.slot_4 = self.root.add_scroll_menu("SLOT-4", 4, 3, row_span=6)
        self.slot_5 = self.root.add_scroll_menu("CHECK-POTION", 4, 4, row_span=2)
        self.slot_6 = self.root.add_scroll_menu("CHECK-PK", 6, 4, row_span=4)

        # collect widgets
        self.root.set_selected_widget(self.slot_1.get_id())
        self.widget_ary = list(root.get_widgets().values())
        self.widget_title_ary = list(map(lambda widget: widget.get_title(), self.widget_ary))

        # add style
        self.monitor.set_selectable(False)
        self.monitor.add_text_color_rule("=", py_cui.WHITE_ON_RED, "contains", match_type='regex')
        self.monitor.add_text_color_rule("-", py_cui.WHITE_ON_BLUE, "contains", match_type='regex')
        self.console.set_selectable(False)
        
        for widget in self.widget_ary:           
            widget.add_text_color_rule("False", py_cui.RED_ON_BLACK, "contains", match_type='regex')
            widget.add_text_color_rule("True", py_cui.BLUE_ON_BLACK, "contains", match_type='regex')
            widget.set_focus_border_color(py_cui.GREEN_ON_BLACK)

        # add event
        self.slot_1.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_1))
        self.slot_2.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_2))
        self.slot_3.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_3))
        self.slot_4.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_4))
        self.slot_5.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_5))
        self.slot_6.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.change_popup(self.slot_6))

        self.slot_1.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_1))
        self.slot_2.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_2))
        self.slot_3.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_3))
        self.slot_4.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_4))
        self.slot_5.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_5))
        self.slot_6.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.change_popup(self.slot_6))

        # apply data
        self.load_data()
        self.update_monitor()
        self.log("App started.")

    def log(self, msg):
        now = time.localtime()
        text = f"[{now.tm_year}-{now.tm_mon}-{now.tm_mday} {now.tm_hour}:{now.tm_min}:{now.tm_sec}]\n{msg}"
        self.console.set_text(text)

    def load_data(self):
        for widget in self.widget_ary:
            widget_title = widget.get_title()
            widget_idx = self.widget_title_ary.index(widget_title)
            if widget_title in self.user_data.keys():
                widget.clear()
                for key, value in self.user_data[widget_title].items():
                    text = f"{key.ljust(8)} : {value}"
                    self.widget_ary[widget_idx].add_item(text)


    def change_widget_text(self, selected_widget, key, value):
        self.user_data[selected_widget][key] = value
        self.load_data()
        self.log(f"{selected_widget} {key} value changed to {value}")

    def change_popup(self, widget):
        selected_widget = widget.get_title()
        key, value = widget.get().split(":")
        key = key.replace(" ", "")
        value = value.replace(" ", "")
        if "USE" in key or "REPEAT" in key:
            # if value type is bool, do not show popup just toggle it.
            self.user_data[selected_widget][key] = False if value == "True" else True
            self.load_data()
            self.log(f"{selected_widget} {key} value changed to {value}")
        else:
            root.show_text_box_popup("Type new value. (Enter/ESC).", lambda value: self.change_widget_text(selected_widget, key, value))

    def progress_bar(self, title, total, current, size, character):
        bar, value = progressBar.filledBar(total, current, size, " ", character)
        return f"{title} {str(int(float(value))).rjust(3)}% [{bar}]"


    def update_monitor(self):
        text = f"{self.progress_bar('HP', 100, 50, 32, '=')}\n"
        text += f"{self.progress_bar('HP', 100, 80, 32, '-')}\n"
        self.monitor.set_text(text)



root = py_cui.PyCUI(10,5)
App(root)
root.start()
