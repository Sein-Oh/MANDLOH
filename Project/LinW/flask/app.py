from flask import Flask, Response, render_template, jsonify
import base64
import cv2
import numpy as np
import dxcam
import json
import serial
import serial.tools.list_ports as sp
import time
from tkinter import filedialog, messagebox
import threading
import os
import window_control as win
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Flask(__name__)
browser_ready = False
ser = None

size_preview = (235, 130)
size_img = (50, 50)

run = {}
windows_ary = []
images = {}
names_ary_prev = []
selected_window = None
current_window = None

param = {
    "timer1_key": "1",
    "timer1_cool": "3",
    "timer2_key": "2",
    "timer2_cool": "3",
    "timer3_key": "3",
    "timer3_cool": "3",

    "hp1_roi": "0,0,200,20",
    "hp1_range": "0,40",
    "hp1_thres": "210",
    "hp1_key": "1",
    "hp1_cool": "3",
    "hp2_roi": "0,0,200,20",
    "hp2_range": "0,40",
    "hp2_thres": "210",
    "hp2_key": "1",
    "hp2_cool": "3",
    "hp3_roi": "0,0,200,20",
    "hp3_range": "0,40",
    "hp3_thres": "210",
    "hp3_key": "1",
    "hp3_cool": "3",
    "hp4_roi": "0,0,200,20",
    "hp4_range": "0,40",
    "hp4_thres": "210",
    "hp4_key": "1",
    "hp4_cool": "3",
    "hp5_roi": "0,0,200,20",
    "hp5_range": "0,40",
    "hp5_thres": "210",
    "hp5_key": "1",
    "hp5_cool": "3",

    "img1_roi": "전체화면",
    "img1_thres": "0.8",
    "img1_key": "1",
    "img1_cool": "3",
    "img1_name": "-",
    "img2_roi": "전체화면",
    "img2_thres": "0.8",
    "img2_key": "1",
    "img2_cool": "3",
    "img2_name": "-",
    "img3_roi": "전체화면",
    "img3_thres": "0.8",
    "img3_key": "1",
    "img3_cool": "3",
    "img3_name": "-",
    "img4_roi": "전체화면",
    "img4_thres": "0.8",
    "img4_key": "1",
    "img4_cool": "3",
    "img4_name": "-",
    "img5_roi": "전체화면",
    "img5_thres": "0.8",
    "img5_key": "1",
    "img5_cool": "3",
    "img5_name": "-"
}


def run_server():
    os.system(f"start msedge --app=http://localhost:8080")
    app.run(port=8080)


def cvToB64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    return str(im_b64)


def add_to_images():
    global images
    name_ary = [param[key] for key in param.keys() if "name" in key]
    for idx, name in enumerate(name_ary):
        if "png" in name.lower() or "jpg" in name.lower():
            try:
                img = cv2.imread(name)
            except:
                img = None
        else:
            img = None
        images[f"img{idx+1}"] = img
        print(images)


@app.route('/')
def index():
    global param, browser_ready, names_ary_prev
    browser_ready = True
    # userdata.json 찾아 반영하기
    if os.path.isfile("userdata.json"):
        print("userdata.json파일을 적용합니다.")
        with open("userdata.json", "r", encoding="UTF8") as file:
            param = json.load(file)
    else:
        print("userdata.json을 찾을 수 없습니다. 기본값으로 시작합니다.")

    names_ary_prev = [param[x] for x in param.keys() if "name" in x]
    add_to_images() #이미지 업데이트
    return render_template("index.html")


@app.route("/request_param")
def send_param():
    return jsonify(param)


@app.route("/update_params/<param_str>")
def get_params(param_str):
    global param, names_ary_prev
    param = json.loads(param_str)
    names_ary = [param[x] for x in param.keys() if "name" in x]
    if names_ary != names_ary_prev:
        names_ary_prev = names_ary
        add_to_images()
        print("이미지 파일명 변경")
    return "OK"


@app.route("/update_run_state/<param_str>")
def get_run_state(param_str):
    global run
    run = json.loads(param_str)
    return "OK"


@app.route("/request_window")
def send_window_ary():
    global windows_ary
    windows_ary = win.get_win_list()
    win_title_ary = [t[0] for t in windows_ary]
    win_title_ary.insert(0, "전체화면")
    data = {"value" : win_title_ary}
    return jsonify(data)


@app.route("/update_window/<data_str>")
def get_windows_combo(data_str):
    global selected_window
    selected_window = data_str
    return "OK"


@app.route("/request_port")
def send_ports_ary():
    ports_ary = []
    for port, desc, hwid in sorted(sp.comports()):
        ports_ary.append(f"{port}, {desc}")
    data = {"value" : ports_ary}
    return jsonify(data)


@app.route("/update_port/<data_str>")
def get_ports_combo(data_str):
    global ser
    port = data_str.split(",")[0]
    ser = serial.Serial(port=port, baudrate=9600)
    print(f"{port}에 연결되었습니다.")
    return "OK"


# a generator with yield expression
def gen_frame():
    global idx
    while True:
        time.sleep(0.5)
        frame_full = cam.get_latest_frame()
        img_preview = cv2.resize(frame_full, dsize=size_preview, interpolation=cv2.INTER_LINEAR)
        img_preview_b64 = cvToB64(img_preview)
        data = {}
        data["preview"] = img_preview_b64
        for key in images.keys():
            if isinstance(images[key], np.ndarray):
                data[key] = cvToB64(images[key])
        
        yield f"data: {json.dumps(data)}\n\n"


@app.route("/update_frame")
def update_frame():
    return Response(gen_frame(), mimetype='text/event-stream')


print("웹서버를 시작합니다.")
threading.Thread(target=run_server, daemon=True).start()

print("캡처를 시작합니다.")
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=2)

print("브라우저 실행을 기다립니다.")
while True:
    if browser_ready: break

while True:
    for key, value in run.items():
        if value == True:
            print(key)

    time.sleep(0.5)
