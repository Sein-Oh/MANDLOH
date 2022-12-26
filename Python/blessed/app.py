from blessed import Terminal
from StringProgressBar import progressBar
from pytimedinput import timedInput
from InquirerPy import inquirer
import json, time
import os, platform

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
    print(f"{term.move_xy(x, y)}HP [{str(value).rjust(3)}%] [{term.red}{bar}{term.normal}]")

def draw_mp_bar(x, y, value):
    bar = progressBar.filledBar(100, value, 30, " ", "=")[0]
    print(f"{term.move_xy(x, y)}MP [{str(value).rjust(3)}%] [{term.blue}{bar}{term.normal}]")

def select_menu():
    return inquirer.rawlist(message="MENU", choices=["SELECT RUNNING FUNCTION", "CHANGE SETTING", "BACK"]).execute()

def select_slot():
    return inquirer.rawlist(message="Slot to change:", choices=["SLOT-1", "SLOT-2", "BACK"]).execute()

def select_key():
    return inquirer.rawlist(message="Value to change:", choices=["HP_MIN", "HP_MAX", "MP_MIN", "MP_MAX", "KEY", "COUNT", "COOLTIME", "REPEAT"]).execute()

def change_value():
    return inquirer.text(message="Type new value").execute()

idx = 0
clear()
while True:
    draw_time(0, 0)
    draw_hp_bar(0, 1, idx)
    draw_mp_bar(0, 2, idx)
    idx += 1
    text, timeout = timedInput("Press Enter to show menu.", timeout=0.2)
    if not timeout:
        clear()
        menu = select_menu()
        if "BACK" in menu:
            pass
        elif "CHANGE" in menu:
            slot = select_slot()
            key = select_key()
            value = change_value()

        clear()
