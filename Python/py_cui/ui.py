import py_cui
import json

root = py_cui.PyCUI(6,5)

def change_widget_text(widget, value):
    items = widget.get_item_list()
    items[items.index(widget.get())] = value
    widget.clear()
    widget.add_item_list(items)

def change_popup(widget):
    global user_data
    key, value = widget.get().split(":")
    value.replace(" ", "")
    # console.set_text(f"{key},{value}")
    widget_title = widget.get_title()
    if "USE" in key or "REPEAT" in key:
        user_data[widget_title][key] = not user_data[widget_title][key]
        console.set_text(user_data)
    # else:
    #     root.show_text_box_popup("Type new value. (Enter/ESC).", lambda value: change_widget_text(widget, value))

monitor = root.add_text_block("MONITOR", 0, 0, column_span=2)
console = root.add_text_block("CONSOLE", 0, 2, column_span=3)

slot_1 = root.add_scroll_menu("SLOT-1", 3, 0, row_span=3)
slot_2 = root.add_scroll_menu("SLOT-2", 3, 1, row_span=3)
slot_3 = root.add_scroll_menu("SLOT-3", 3, 2, row_span=3)
slot_4 = root.add_scroll_menu("SLOT-4", 3, 3, row_span=3)
slot_5 = root.add_scroll_menu("CHECK-POTION", 3, 4, row_span=1)
slot_6 = root.add_scroll_menu("CHECK-PK", 4, 4, row_span=2)
for i in range(1, 7):
    exec(f"slot_{i}.add_mouse_command(py_cui.keys.LEFT_MOUSE_DBL_CLICK, lambda: change_popup(slot_{i}))")
    exec(f"slot_{i}.add_key_command(py_cui.keys.KEY_ENTER, lambda: change_popup(slot_{i}))")

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
        widget.set_focus_border_color(py_cui.GREEN_ON_BLACK)
        widget.set_selected_color(py_cui.GREEN_ON_BLACK)
        for key, value in user_data[widget_title].items():
            text = f"{key.ljust(8)} : {value}"
            widget_ary[widget_idx].add_item(text)

root.start()
