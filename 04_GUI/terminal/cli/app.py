from pytimedinput import timedKey
from InquirerPy import inquirer
import os
import json
import msvcrt
import time

def load_data(name):
    with open(name, "r") as f:
        return json.load(f)

def select_slot():
    return inquirer.rawlist(message="Slot to change:", choices=["SLOT1", "SLOT2", "SLOT3", "SLOT4", "SLOT5", "BACK"]).execute()

def select_key():
    return inquirer.rawlist(message="Value to change:", choices=["USE", "HP_MIN", "HP_MAX", "MP_MIN", "MP_MAX", "KEY", "COUNT", "COOLTIME", "REPEAT"]).execute()

def clear():
    os.system("cls")
    print("START")

def main_log(msg):
    now = time.localtime()
    text = f"[{now.tm_mon}-{now.tm_mday} {now.tm_hour}:{now.tm_min}:{str(now.tm_sec).rjust(2, '0')}] : {msg}"
    print(text, end="")
    print("\b" * len(text), end="", flush=True)

data = load_data("user_data.json")
clear()

while True:
    main_log("HELLO WORLD!!")
    if msvcrt.kbhit():
        clear()
        select = inquirer.rawlist(message="Select menu:", choices=["Change setting", "BACK"]).execute()
        if select == "Change setting":
            slot = select_slot()
            print("Current your values.")
            print("==========================")
            for key, value in data[slot].items():
                print(key.ljust(8), ":", value)
            print("==========================")
            
            key = select_key()
            if key == "USE" or "REPEAT":
                data[slot][key] = not data[slot][key]
                print(f"{slot}-{key} : {data[slot][key]}")
                time.sleep(2)
        clear()
    time.sleep(0.2)


