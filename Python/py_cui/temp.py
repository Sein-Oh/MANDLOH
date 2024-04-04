import py_cui
import time
import threading

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
        self.root = root
        self.root.set_title("MANDLOH")
        self.root.set_refresh_timeout(0.01)
        #self.root.toggle_unicode_borders()

        self.btn = self.root.add_button("TEST", 0, 0, command=self.test)
        self.btn.set_color(6)

        self.toggle = self.root.add_button("TOGGLE", 0, 1, command=lambda: self.toggle_evt(self.toggle))
        self.toggle.on = False
        #self.toggle.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: self.toggle_evt(self.toggle))
        #self.toggle.add_key_command(py_cui.keys.KEY_ENTER, lambda: self.toggle_evt(self.toggle))

        self.log_box = self.root.add_text_block("CONSOLE", 5, 0, row_span=5, column_span=5)
        self.log_box.set_selectable(False)
        self.log_box_ary = ["" for x in range(7)]

        self.log("App started.")
        self.count = 0
        # threading.Thread(target=self.upcount, daemon=True).start()

    def log(self, msg):
        now = time.localtime()
        text = f"[{str(now.tm_hour).zfill(2)}:{str(now.tm_min).zfill(2)}:{str(now.tm_sec).zfill(2)}] : {msg}"
        self.log_box_ary.pop(0)
        self.log_box_ary.append(text)
        log_msg = ""
        for msg in self.log_box_ary:
            log_msg += msg + "\n"
        self.log_box.set_text(log_msg)

    def test(self):
        self.root.show_menu_popup("MENU", ["A", "B", "C"], command=self.select_menu)

    def select_menu(self, result):
        self.log(result)

    def toggle_evt(self, widget):
        widget.on = not widget.on
        widget.set_color(6 if widget.on else 3)
        

    def upcount(self):
        while True:
            self.log(self.count)
            self.count += 1
            time.sleep(0.1)


root = py_cui.PyCUI(10,5)
App(root)
root.start()
