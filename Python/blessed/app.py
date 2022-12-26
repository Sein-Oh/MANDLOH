from blessed import Terminal
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
 
def draw_time(x, y):
    now = time.localtime()
    print(f"{term.move_xy(x, y)}{now.tm_mon}-{now.tm_mday} {now.tm_hour}:{now.tm_min}:{str(now.tm_sec).rjust(2, '0')}")
 
def draw_hp_bar(x, y, value):
    bar = progressBar.filledBar(100, value, 30, " ", "=")[0]
    print(f"{term.move_xy(x, y)}HP  : {str(value).rjust(3)}% [{term.red}{bar}{term.normal}]")
 
def draw_mp_bar(x, y, value):
    bar = progressBar.filledBar(100, value, 30, " ", "=")[0]
    print(f"{term.move_xy(x, y)}MP  : {str(value).rjust(3)}% [{term.blue}{bar}{term.normal}]")

def draw_running_func(x, y):
    running = []
    for key in list(data.keys()):
        if data[key]["USE"]: running.append(key)
    text = "NONE" if len(running) < 1 else ','.join(running)
    print(f"{term.move_xy(x, y)}RUN : {text}")

def draw_dict(data):
    print("==========================")
    for key, value in data.items():
        print(f"{key.ljust(8)} : {value}")
    print("==========================")    

def draw_all_dict(x, y):
    idx = 0
    for slot in data.keys():
        text = ' / '.join(f"{key}:{value}" for key, value in data[slot].items())
        print(f"{term.move_xy(x, y+idx)}{slot} : {text}")
        idx += 1

def select_menu():
    clear()
    menu = inquirer.rawlist(message="SELECT MENU : ", choices=["CHANGE VALUE", "RETURN TO HOME"]).execute()
    if "RETURN TO HOME" in menu: return
    elif "CHANGE" in menu: select_slot()

def select_slot():
    menus = list(data.keys())
    menus.append("RETURN TO HOME")
    slot = inquirer.rawlist(message="SELECT SLOT : ", choices=menus).execute()
    if "RETURN TO HOME" in slot: return
    else: select_key(slot)
 
def select_key(slot):
    draw_dict(data[slot])
    menus = list(data[slot].keys())
    menus.append("RETURN TO HOME")
    key = inquirer.rawlist(message="SELECT VALUE : ", choices=menus).execute()
    if "RETURN TO HOME" in key: return
    elif "USE" in key or "REPEAT" in key:
        data[slot][key] = not data[slot][key]
    elif "HP" in key or "MP" in key:
        data[slot][key] = inquirer.text(message="NEW VALUE ex) 0~80 : ").execute()
    elif "KEY" in key:
        data[slot][key] = inquirer.text(message="NEW VALUE ex) 8 : ").execute()
    elif "COUNT" in key:
        data[slot][key] = inquirer.number(message="NEW VALUE ex) 1 : ").execute()
    elif "DELAY" in key or "COOLTIME" in key:
        data[slot][key] = float(inquirer.number(message="NEW VALUE ex) 0.5 : ").execute())
    clear()

data = load_data("userdata.json")
idx = 0
clear()
while True:
    draw_time(0, 0)
    draw_text(0, 1, "<STATUS>")
    draw_hp_bar(0, 2, idx)
    draw_mp_bar(0, 3, idx)
    draw_text(0, 5, "<SETTING>")
    draw_all_dict(0, 6)
    idx += 1
    print("")
    text, timeout = timedInput("Press Enter to show menu.", timeout=0.2)
    if not timeout:
        select_menu()


