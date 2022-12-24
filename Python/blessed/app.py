from blessed import Terminal
from art import text2art
from StringProgressBar import progressBar
from InquirerPy import inquirer
import json, time

term = Terminal()
print(term.clear())

def draw_figlet(x, y, text, color=term.normal):
    figlet = text2art(text)
    figlet_ary = figlet.split("\n")
    figlet_width = 0
    for i in figlet_ary:
        figlet_width = len(i) if len(i) > figlet_width else figlet_width
    print(f"{term.move_xy(x, y)}{color}{'=' * figlet_width}")
    print(f"{term.move_xy(x, y+1)}{figlet}")
    print(f"{term.move_xy(x, y+6)}{'=' * figlet_width}{term.normal}")

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

def load_data(name):
    with open(name, "r") as f:
        return json.load(f)

def select_slot():
    return inquirer.rawlist(message="Slot to change:", choices=["SLOT1", "SLOT2", "SLOT3", "SLOT4", "SLOT5", "BACK"]).execute()

def select_key():
    return inquirer.rawlist(message="Value to change:", choices=["USE", "HP_MIN", "HP_MAX", "MP_MIN", "MP_MAX", "KEY", "COUNT", "COOLTIME", "REPEAT"]).execute()


draw_figlet(0, 1, "LINEAGE-W", term.orangered)
idx = 0
while True:
    draw_time(0, 0)
    draw_hp_bar(0, 8, idx)
    # draw_mp_bar(0, 8, idx)
    idx += 1
    key = term.inkey(timeout=0.5)
    # if key.name == "KEY_ENTER":

