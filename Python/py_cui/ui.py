import py_cui
import json

root = py_cui.PyCUI(3,5)
root.add_key_command(py_cui.keys.KEY_Q_LOWER, lambda:root.stop())

monitor = root.add_text_block("MONITOR", 0, 0, column_span=2)
console = root.add_text_block("CONSOLE", 0, 2, column_span=3)

slot_1 = root.add_scroll_menu("SLOT-1", 1, 0, row_span=2)
slot_2 = root.add_scroll_menu("SLOT-2", 1, 1, row_span=2)
slot_3 = root.add_scroll_menu("SLOT-3", 1, 2, row_span=2)
slot_4 = root.add_scroll_menu("SLOT-4", 1, 3, row_span=2)
slot_5 = root.add_scroll_menu("CHECK-POTION", 1, 4)
slot_6 = root.add_scroll_menu("CHECK-PK", 2, 4)

widget_ary = list(root.get_widgets().values())
widget_title_ary = list(map(lambda t: t.get_title(), widget_ary))

with open("userdata.json", "r") as f:
    user_data = json.load(f)

for num, widget in root.get_widgets().items():
    widget_title = widget.get_title()
    widget_idx = widget_title_ary.index(widget_title)
    # print(f"{widget_title}-{widget_idx}")
    if widget_title in user_data.keys():
        widget.clear()
        widget.add_text_color_rule("False", py_cui.RED_ON_BLACK, "contains", match_type='regex')
        widget.add_text_color_rule("True", py_cui.BLUE_ON_BLACK, "contains", match_type='regex')
        for key, value in user_data[widget_title].items():
            text = f"{key.ljust(8)} : {value}"
            widget_ary[widget_idx].add_item(text)

root.start()
