from blessed import Terminal
from blessedtable import Blessedtable
from StringProgressBar import progressBar
from pytimedinput import timedInput
from InquirerPy import inquirer
import json, time, os, platform
 
term = Terminal()
 
def clear():
    command = "cls" if "Windows" in platform.platform() else "clear"
    os.system(command)
 
def load_data(name):
    with open(name, "r") as f:
        return json.load(f)
 
def draw_text(x, y, text, color=term.normal):
    print(f"{term.move_xy(x, y)}{color}{text}{term.normal}")
 
def draw_time(x, y, color=term.normal):
    now = time.localtime()
    print(f"{term.move_xy(x, y)}{color}[{now.tm_mon}-{now.tm_mday} {now.tm_hour}:{now.tm_min}:{str(now.tm_sec).rjust(2, '0')}]{term.normal}")
 
def draw_hp_bar(x, y, value):
    bar = progressBar.filledBar(100, value, 30, " ", "=")[0]
    print(f"{term.move_xy(x, y)}HP : {str(value).rjust(3)}% [{term.red}{bar}{term.normal}]")
 
def draw_mp_bar(x, y, value):
    bar = progressBar.filledBar(100, value, 30, " ", "=")[0]
    print(f"{term.move_xy(x, y)}MP : {str(value).rjust(3)}% [{term.blue}{bar}{term.normal}]")

def draw_dict(data):
    table = Blessedtable()
    table.set_deco(3)
    title = ["USE", "HP", "MP", "KEY", "COUNT", "DELAY", "COOLTIME", "REPEAT"]
    table.add_rows([title])
    items = []
    keys = list(data.keys())
    for t in title:
        if t in keys:
            items.append(str(data[t]))
        else:
            items.append("-")
    table.add_row(items)
    table.set_cols_align(["c", "c", "c", "c", "c", "c", "c", "c"])
    table.set_cols_width([8,8,8,8,8,8,8,8])
    print(table.draw())

def select_menu():
    clear()
    menu = inquirer.rawlist(message="SELECT MENU : ", choices=["CHANGE SETTING", "RETURN TO HOME"]).execute()
    if "RETURN TO HOME" in menu: return
    elif "CHANGE" in menu: select_slot()

def select_slot():
    menus = list(data.keys())
    menus.append("RETURN TO HOME")
    slot = inquirer.rawlist(message="SELECT SLOT : ", choices=menus).execute()
    if "RETURN TO HOME" in slot: return
    else: select_key(slot)
 
def select_key(slot):
    while True:
        clear()
        print(f"{term.on_green}== {slot} =={term.normal}")
        draw_dict(data[slot])
        menus = list(data[slot].keys())
        menus.append("RETURN TO HOME")
        key = inquirer.rawlist(message="SELECT VALUE : ", choices=menus).execute()
        if "RETURN TO HOME" in key:
            draw_unchanged_widget()
            return
        elif "USE" in key or "REPEAT" in key:
            data[slot][key] = not data[slot][key]
        elif "HP" in key or "MP" in key:
            data[slot][key] = inquirer.text(message="NEW VALUE : ").execute()
        elif "KEY" in key:
            data[slot][key] = inquirer.text(message="NEW VALUE : ").execute()
        elif "COUNT" in key:
            data[slot][key] = inquirer.number(message="NEW VALUE : ").execute()
        elif "DELAY" in key or "COOLTIME" in key:
            data[slot][key] = float(inquirer.number(message="NEW VALUE : ").execute())

def draw_table(x, y):
    table = Blessedtable()
    table.set_deco(3)
    title = ["SLOT", "USE", "HP", "MP", "KEY", "COUNT", "DELAY", "COOLTIME", "REPEAT"]
    table.add_rows([title])
    for slot in list(data.keys()):
        items = [slot]
        keys = list(data[slot].keys())
        for t in title:
            if t == "SLOT":
                pass
            elif t in keys:
                items.append(str(data[slot][t]))
            else:
                items.append("-")
        table.add_row(items)
    table.set_cols_align(["c", "c", "c", "c", "c", "c", "c", "c", "c"])
    table.set_cols_width([12,8,8,8,8,8,8,8,8])
    print(f"{term.move_xy(x, y)}{table.draw()}")

def draw_unchanged_widget():
    clear()
    draw_text(0, 1, "[STATUS]", term.on_green)
    draw_text(0, 7, "[SETTING]", term.on_green)
    draw_table(0, 8)

data = load_data("userdata.json")
idx = 0
draw_unchanged_widget()

while True:
    draw_time(0, 0, term.on_blue)
    draw_hp_bar(0, 2, idx)
    draw_mp_bar(0, 3, idx)
    print("")
    text, timeout = timedInput("Press Enter to show menu.", timeout=0.2)
    if not timeout:
        select_menu()
    idx += 1
    
