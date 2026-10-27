import cv2
import dxcam
import numpy as np
import threading
import win32gui
import json
import serial
import time

app = {
    "capture": "fullscreen",
    "arduino_port" : "COM10",
    "resize": [1280, 720],
    "telegram_token": "",
	"telegram_chat_id": ""
}


timer = {
    "F연타": {
        "key": "f",
        "cooltime": 0.2
    }
}

hpslot = {
    "귀환": {
        
        "key": "8",
        "cooltime": 20,
        "roi": [92, 32, 283, 38],
        "thres": 210,
        "range": [0, 40]
    },
    "텔": {
        "key": "7",
        "cooltime": 10,
        "roi": [92, 32, 283, 38],
        "thres": 210,
        "range": [41, 60]
    },
    "힐": {
        "key": "4",
        "cooltime": 3,
        "roi": [92, 32, 283, 38],
        "thres": 210,
        "range": [41, 85]
    }
}

imgslot = {
    "Assist": {
        "file": "assist.png",
        "key": "1",
        "cooltime": 5,
        "roi": [1046, 440, 1245, 625],
        "thres": 0.9
    }
}

def load_img(path):
    # 한글지원
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img

run = {}
cooling = {}
img = {}
values = {}

for slot in timer.keys():
    run[slot] = False
    cooling[slot] = False

for slot in hpslot.keys():
    run[slot] = False
    cooling[slot] = False

for slot in imgslot.keys():
    run[slot] = False
    cooling[slot] = False
    img[slot] = load_img(imgslot[slot]["file"])




def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

def find_window(target):
    win_ary = get_win_list()
    for win in win_ary:
        if target in win[0]:
            target_text = win[0]
            target_hwnd = win[1]
    return target_hwnd, target_text

def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

def find_img(background, target):
    h, w, _ = target.shape
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    max_val = round(max_val, 2)
    return x, y, w, h, max_val

def calc_hp(img_hp, thres_min=210):
    hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
    hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
    hpThres = cv2.threshold(hpBlur, thres_min, 255, cv2.THRESH_BINARY)[1]
    hpThres_img = cv2.cvtColor(hpThres, cv2.COLOR_GRAY2BGR)
    hpPoint = np.flip(hpThres).argmax()
    hpPoint = 100 if hpPoint >= hpThres.shape[1] else int((1-(np.flip(hpThres).argmax() / hpThres.shape[1])) * 100)
    return hpPoint, hpThres_img

def cool_down(key):
    cooling[key] = False

def cool_run(key, sec):
    cooling[key] = True
    threading.Timer(sec, cool_down, args=[key]).start()


def send_keys(keys):
    for key in keys:
        print(key)

cam = dxcam.create(output_color="BGR")
cam.start(target_fps=5)

ser = serial.Serial(port=app["arduino_port"], baudrate=9600)


if app["capture"] != "fullscreen":
    target_hwnd, target_text = find_window(app["capture"])
    print(target_text)

def loop():
    while True:
        if app["capture"] == "fullscreen":
            frame = cam.get_latest_frame()
        else:
            x1, y1, x2, y2 = get_win_size(target_hwnd)
            frame = cam.get_latest_frame()[y1:y2, x1:x2]
        
        resize = app["resize"]
        if isinstance(resize, list):
            frame = cv2.resize(frame, dsize=(resize[0], resize[1]), interpolation=cv2.INTER_AREA)
        
        cv2.imshow("frame", frame)
        key = cv2.waitKey(1)

        for key in timer.keys():
            if run[key] == True and cooling[key] == False:
                cool_run(key, timer[key]["cooltime"])
                send_keys(timer[key]["key"])
        
        for key in hpslot.keys():
            if run[key] == True:
                roi = frame[hpslot[key]["roi"][1]:hpslot[key]["roi"][3], hpslot[key]["roi"][0]:hpslot[key]["roi"][2]]
                hp, thres_img = calc_hp(roi, hpslot[key]["thres"])
                
                # cv2.imshow(f"{key}", cv2.vconcat([roi, thres_img]))
                # cv2.waitKey(1)

                if hp >= hpslot[slot]["range"][0] and hp <= hpslot[slot]["range"][1] and cooling[key] == False:
                    cool_run(key, hpslot[key]["cooltime"])
                    send_keys(hpslot[key]["key"])
                    
        time.sleep(0.2)

threading.Thread(target=loop, daemon=True).start()

while True:
    command = input("Your command : ")
    exec(command)
