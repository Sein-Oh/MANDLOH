import py_cui
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
        self.root = root
        self.root.set_title("MANDLOH")
        self.root.toggle_unicode_borders()

        self.btn = self.root.add_button("TEST", 0, 0, command=self.test)

        self.log_box = self.root.add_text_block("CONSOLE", 5, 0, row_span=5, column_span=5)
        self.log_box.set_selectable(False)
        self.log_box_ary = ["" for x in range(7)]

        self.log("App started.")

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
        self.log("Hello")

root = py_cui.PyCUI(10,5)
App(root)
root.start()
