import FreeSimpleGUI as sg
import os
import json
import time
import dxcam
import cv2
import numpy as np

sg.theme("Default1")
script_path = os.path.dirname(__file__)

cam = dxcam.create(output_color="BGR")
cam.start(target_fps=30)
frame = cam.get_latest_frame()


def loop():
    while True:
        frame = cam.get_latest_frame()
        img = cv2.resize(frame, dsize=(320,240), interpolation=cv2.INTER_LINEAR)
        window.write_event_value("loop", img)


layout = [
    [sg.Image("", background_color="gray", size=(320,240), key="img")],
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
            with open(file, "r") as f:
                data = json.load(f)
                data["name"] = name
                print(data)
                
    elif event == "Pause":
        new_row = [
            sg.Text("New")
        ]
        window.extend_layout(window["container"], [new_row])
        
    elif event == "loop":
        img = value["loop"]
        window["img"].update(data=cv2.imencode(".ppm", img)[1].tobytes())

window.close()
