import FreeSimpleGUI as sg
import os
import json
import time
import dxcam
import cv2
import numpy as np
import threading

sg.theme("Default1")

cam = dxcam.create(output_color="BGR")
cam.start(target_fps=10)
frame = cam.get_latest_frame()
screen_height, screen_width, _ = frame.shape

widget_width = 320
widget_height = int(screen_height / (screen_width / widget_width))

slots = {}

def load_img(path):
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img


def find_img(background, targets):
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    
    best_val = -1
    best_result = (0, 0, 0, 0, 0)
    
    for target in targets:
        h, w = target.shape
        res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val > best_val:
            x, y = max_loc
            best_val = max_val
            best_result = (x, y, w, h, round(max_val, 2))
    return best_result


def cooling_off(key):
    slots[key]["cooling"] = False


def cooling_on(key, t):
    slots[key]["cooling"] = True
    th = threading.Timer(t, cooling_off, [key])
    th.daemon = True
    th.start()


def make_timer_slot(name):
    new_row = [sg.Checkbox(name, size=(6,1), key=f"cb_{name}"), sg.Text(f'[{float(slots[name]["cooltime"])}] {slots[name]["key"]}', size=(27,1))]
    return new_row


def make_image_slot(name):
    try:
        targets_list = slots[name]["target"]
        targets_ary = []
        for target in targets_list:
            img = load_img(f"resources/{target}")
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            targets_ary.append(img_gray)
        slots[name]["targets"] = targets_ary
        new_row = [sg.Checkbox(name, size=(6,1), key=f"cb_{name}"), sg.Text(f'[{float(slots[name]["cooltime"])}][0>0] {slots[name]["key"]}', size=(27,1), key=f"lb_{name}")]
        return new_row
    except:
        print("Image load failed.")


def loop():
    while True:
        frame = cam.get_latest_frame()
        window.write_event_value("loop", frame)


layout = [
    [sg.Frame("Preview", [[sg.Image("", background_color="gray", size=(widget_width,widget_height), key="img")]])],
    [sg.Button("Load", expand_x=True), sg.Button("Pause", expand_x=True)],
    [sg.Column([], key="container", vertical_scroll_only=True)]
]

window = sg.Window("Timer maker", layout, finalize=True)
window.start_thread(loop)


while True:
    event, value = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    
    elif event == "Load":
        filename = sg.popup_get_file("Select file", default_path=os.getcwd(), no_window=True, multiple_files=True)
        for file in filename:
            name = file.split("/")[-1].split(".")[0]
            with open(file, "r", encoding="utf-8") as f:
                slots[name] = json.load(f)
                slots[name]["cooling"] = False
                if slots[name]["type"] == "timer":
                    window.extend_layout(window["container"], [make_timer_slot(name)])
                elif slots[name]["type"] == "image":
                    window.extend_layout(window["container"], [make_image_slot(name)])
                
    elif event == "Pause":
        print(slots)
        
    elif event == "loop":
        frame = value["loop"]
        img = cv2.resize(frame, dsize=(widget_width,widget_height), interpolation=cv2.INTER_LINEAR)
        window["img"].update(data=cv2.imencode(".ppm", img)[1].tobytes())
        
        for key in slots:
            if slots[key]["type"] == "timer": #Timer
                if window[f"cb_{key}"].get() == True: #Checkbox
                    if slots[key]["cooling"] == False: #Cooling
                        command = slots[key]["key"]
                        cooltime = float(slots[key]["cooltime"])
                        cooling_on(key, cooltime)
                        print(f"[{cooltime}][{key}]")
                        
            elif slots[key]["type"] == "image": #image
                roi = slots[key]["roi"]
                background = frame[roi[1]:roi[3], roi[0]:roi[2]]
                result = find_img(background, slots[key]["targets"])
                max_val = result[4]
                window[f"lb_{key}"].update(f'[{float(slots[name]["cooltime"])}][{float(max_val)}>{slots[key]["threshold"]}] {slots[name]["key"]}')
                if window[f"cb_{key}"].get() == True: #Checkbox
                    if slots[key]["cooling"] == False: #Cooling
                        command = slots[key]["key"]
                        cooltime = float(slots[key]["cooltime"])
                        cooling_on(key, cooltime)
                        print(f"[{cooltime}][{key}]")

window.close()
