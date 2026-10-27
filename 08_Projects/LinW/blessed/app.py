import os
import sys
import threading
import time

from blessed import Terminal
from datetime import datetime

import cv2
import numpy as np
import requests
import subprocess

#Windows only
if sys.platform == "win32":
    import win32gui
    app_hwnd = win32gui.GetForegroundWindow()
    win32gui.MoveWindow(app_hwnd, 1450, 0, 450, 1000, True)
    py_ary = [j for j in os.listdir(".") if ".py" in j]
    for py in py_ary:
        if "server" in py:
            server = subprocess.Popen(["python", py])


fps = 4

#Y700 setup
app_data = {
    "stream_url": "http://127.0.0.1:8000",
    "input_url": "http://127.0.0.1:8000/input",
    "resize": "",
    "telegram chat id": "935941732",
    "telegram token": "1480350910:AAFwyDTBFcwQi7Y_iHXqPkbC4XIAPZ4x81c"
}

slot = {
    "Heal": {
        "type": "hp",
        "key": "4",
        "cooltime": "2",
        "min range": "0",
        "max range": "85",
        "x1": "92",
        "y1": "32",
        "x2": "283",
        "y2": "38",
        "threshold": "210"
    },
    "HOME": {
        "type": "hp",
        "key": "8",
        "cooltime": "20",
        "min range": "0",
        "max range": "40",
        "x1": "92",
        "y1": "32",
        "x2": "283",
        "y2": "38",
        "threshold": "210"
    },
    "TELL": {
        "type": "hp",
        "key": "7",
        "cooltime": "5",
        "min range": "41",
        "max range": "60",
        "x1": "92",
        "y1": "32",
        "x2": "283",
        "y2": "38",
        "threshold": "210"
    },
    "PK-HOME": {
        "type": "img",
        "key": "8",
        "cooltime": "5",
        "img": "pk.png",
        "x1": "995",
        "y1": "430",
        "x2": "1150",
        "y2": "616",
        "threshold": "0.75"
    }
}


term = Terminal()
cam = cv2.VideoCapture(app_data["stream_url"])
resize = list(map(int, app_data["resize"].split())) if app_data["resize"] else False
print(f"Resize : {resize}")

if not os.path.isdir("capture"):
    os.system("mkdir capture")

def load_img(path): #한글지원
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img


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
    slot[key]["cooling"] = False


def cool_run(key, sec):
    slot[key]["cooling"] = True
    threading.Timer(sec, cool_down, args=[key]).start()


def tele_send_msg(msg):
    try:
        token = app_data["telegram token"]
        chat_id = app_data["telegram chat id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
        requests.get(url)
    except:
        print("텔레그램 메세지 보내기 실패.")

def tele_send_photo(filename, caption):
    try:
        token = app_data["telegram token"]
        chat_id = app_data["telegram chat id"]
        data = {"chat_id": chat_id, "caption": caption}
        url = f"https://api.telegram.org/bot{token}/sendphoto?chat_id={chat_id}"
        with open(filename, "rb") as f:
            requests.post(url, data=data, files={"photo": f})
    except:
        print("텔레그램 사진 보내기 실패")


def send_keys(keys, frame):
    key_ary = keys.split(" ")
    for key in key_ary:
        if "-" in key:
            time.sleep(float(key[1:]))
        elif "," in key:
            mx, my = list(map(int, key.split(",")))
            cmd = f"{mx},{my}"
            requests.get(f"{app_data['input_url']}/{cmd}")
        elif "noti" in key:
            #noti(msg)
            msg = key.split("(")[1].split(")")[0]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
        elif "photo" in key:
            #photo(msg)
            msg = key.split("(")[1].split(")")[0]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()

        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        else:
            requests.get(f"{app_data['input_url']}/{key}")


def loop():
    global loop_fps, t_prev
    while True:
        ret, frame = cam.read()
        if resize:
            frame = cv2.resize(frame, dsize=(resize[0], resize[1]), interpolation=cv2.INTER_AREA)

        for name in slot.keys():
            if slot[name]["type"] == "timer":
                if slot[name]["run"] == True:
                    if slot[name]["cooling"] == False:
                        key = slot[name]["key"]
                        cooltime = float(slot[name]["cooltime"])
                        cool_run(name, cooltime)
                        send_keys(key, frame)

            elif slot[name]["type"] == "hp":
                if slot[name]["run"] == True:
                    key = slot[name]["key"]
                    cooltime = float(slot[name]["cooltime"])
                    x1 = int(slot[name]["x1"])
                    y1 = int(slot[name]["y1"])
                    x2 = int(slot[name]["x2"])
                    y2 = int(slot[name]["y2"])
                    thres = float(slot[name]["threshold"])
                    min_hp = int(slot[name]["min range"])
                    max_hp = int(slot[name]["max range"])
                    roi = frame[y1:y2, x1:x2]
                    hp, thres_img = calc_hp(roi, thres)
                    slot[name]["value"] = hp
                    
                    if hp >= min_hp and hp <= max_hp and slot[name]["cooling"] == False:
                        cool_run(name, cooltime)
                        send_keys(key, frame)

            elif slot[name]["type"] == "img":
                if slot[name]["run"] == True:
                    key = slot[name]["key"]
                    cooltime = float(slot[name]["cooltime"])
                    x1 = int(slot[name]["x1"])
                    y1 = int(slot[name]["y1"])
                    x2 = int(slot[name]["x2"])
                    y2 = int(slot[name]["y2"])
                    thres = float(slot[name]["threshold"])
                    roi = frame[y1:y2, x1:x2]
                    _x, _y, _w, _h, max_val = find_img(roi, slot[name]["img_data"])
                    found = True if max_val >= thres else False
                    slot[name]["value"] = max_val

                    if found == True and slot[name]["cooling"] == False:
                        cool_run(name, cooltime)
                        send_keys(key, frame)
        t = time.time()
        loop_fps = int(1/(t-t_prev))
        t_prev = t
        
        time.sleep(1/fps)


def draw():
    with term.location(0, 0):
        clock = datetime.now().time()
        print(f"{term.snow(f'[{clock:%T}] FPS:{loop_fps}')}")
        print(term.lawngreen("== INPUT MODE ==".center(46) if input_mode else " ".center(46)))
        for idx, name in enumerate(slot.keys()):
            name_tag = f"{idx+1}) == {name} ".ljust(46, "=")
            print(name_tag)
            run = term.lawngreen(str(slot[name]['run']).ljust(5)) if slot[name]["run"] else term.red(str(slot[name]['run']).ljust(5))
            print(f"   {'RUN'.ljust(10)} : {run}")
            print(f"   {'KEY'.ljust(10)} : {slot[name]['key']}")
            if slot[name]["type"] == "hp":
                print(f"   {'RANGE'.ljust(10)} : {slot[name]['min range']}~{slot[name]['max range']}")
                print(f"   {'VALUE'.ljust(10)} : {str(slot[name]['value']).ljust(6)}")
            elif slot[name]["type"] == "img":
                print(f"   {'THRESHOLD'.ljust(10)} : {slot[name]['threshold']}")
                print(f"   {'VALUE'.ljust(10)} : {str(slot[name]['value']).ljust(6)}")
        print("")
        print(term.snow(f"(Q):앱 종료  (C):화면 정리  (0):선택 해제"))
        print(term.snow(f"(ENTER):INPUT MODE - (1~9):기능 선택"))

for name in slot.keys():
    slot[name]["run"] = False
    slot[name]["cooling"] = False
    slot[name]["value"] = None
    if slot[name]["type"] == "img":
        slot[name]["img_data"] = load_img(slot[name]["img"])

threading.Thread(target=loop, daemon=True).start()
loop_fps = 0
t_prev = time.time()
input_mode = False

print(term.clear())
with term.cbreak(), term.hidden_cursor():
    while True:
        draw()
        val = term.inkey(timeout=0.5)
        key = val.name if val.is_sequence else val
        
        if key == "q":
            print(term.clear())
            try: server.terminate()
            except: pass
            break
        
        elif key == "0":
            for name in slot.keys():
                slot[name]["run"] = False
        
        elif key == "c":
            print(term.clear())
        
        elif key == "KEY_ENTER":
            input_mode = not input_mode
        
        if input_mode == True:
            try:
                num = int(key)
                for idx, name in enumerate(slot.keys()):
                    if num == (idx+1):
                        slot[name]["run"] = not slot[name]["run"]
            except: pass
