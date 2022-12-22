from pytimedinput import timedKey
from InquirerPy import inquirer
import os
import json
from rich import print

def load_data(name):
    with open(name, "r") as f:
        return json.load(f)

def select_slot():
    return inquirer.rawlist(message="Slot to change:", choices=["SLOT1", "SLOT2", "SLOT3", "SLOT4", "SLOT5", "BACK"]).execute()

def select_key():
    return inquirer.rawlist(message="Value to change:", choices=["USE", "HP_MIN", "HP_MAX", "MP_MIN", "MP_MAX", "KEY", "COUNT", "COOLTIME", "REPEAT"]).execute()

data = load_data("user_data.json")


while True:
    msg = f"[red]HP:100[/red] / [blue]MP:100[/blue]"
    print(msg, end="")
    text, timeout = timedKey("", 0.2)
    if not timeout:
        os.system("cls")
        select = inquirer.rawlist(message="Select menu:", choices=["Change setting", "BACK"]).execute()
        if select == "Change setting":
            slot = select_slot()
            print("Current your values.")
            print(data[slot])
            key = select_key()
            if key == "USE" or "REPEAT":
                data[slot][key] = not data[slot][key]
                print(f"{slot}-{key} : {data[slot][key]}")


