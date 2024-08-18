from tkinter import *
import PIL.Image, PIL.ImageTk

import cv2
import numpy as np
import requests
import threading
import time
import os

import dxcam
import serial
import win32gui

fps = 10

if not os.path.isdir("capture"):
    os.system("mkdir capture")


def read_txt(path):
    with open(path, "r", encoding="UTF-8") as file:
        raw_file = file.readlines()
        file = list(map(lambda s: s.strip(), raw_file))
        file = [f for f in file if f] #빈칸 제거용
        return file
    

def convert_data(data_path):
    result = {}
    for data in read_txt(data_path):
        title, value = list(map(lambda s: s.strip(), data.split(":")))
        result[title] = value
    return result


def convert_app_data(data_path):
    result = {}
    for data in read_txt(data_path):
        d = list(map(lambda s: s.strip(), data.split(":")))
        if len(d) > 2:
            temp = ""
            for i in range(1, len(d)):
                temp += d[i] + ":"
            title = d[0]
            value = temp[:-1]
        else:
            title, value = d
        result[title] = value
    return result


def load_img(path): #한글지원
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img


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
            if app_data["capture"] != "fullscreen":
                x1, y1, x2, y2 = get_win_size(target_hwnd)
            else:
                x1, y1, x2, y2 = 0, 0, 0, 0
            mx, my = list(map(int, key.split(",")))
            mx, my = mx + x1, my + y1
            cmd = f"{mx},{my}"
            ser.write(cmd.encode())            

        elif "noti" in key:
            #noti(msg)
            msg = key.split("(")[1].split(")")[0]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
            print(f"Send noti : {msg}")
        elif "photo" in key:
            #photo(msg)
            msg = key.split("(")[1].split(")")[0]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()
            print(f"Send photo : {msg}")

        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        else:
            try:
                ser.write(key.encode())
            except:
                pass
            
app_data = convert_app_data("app.txt")
# Windows Part
print(app_data["capture"])
if app_data["capture"] != "fullscreen":
    target_hwnd, target_text = find_window(app_data["capture"])

resize = list(map(int, app_data["resize"].split())) if app_data["resize"] else False
print(resize)
ser = serial.Serial(port=app_data["arduino port"], baudrate=9600)

slot = {}
txt_ary = [j for j in os.listdir("data") if ".txt" in j]
for txt in txt_ary:
    name = txt.split(".")[0]
    slot[name] = convert_data(f"data/{txt}")
    slot[name]["cooling"] = False
    slot[name]["run"] = False

    if slot[name]["type"] == "img":
        slot[name]["img_data"] = load_img(f"data/{slot[name]['img']}")


class MainWindow(Tk):
    def __init__(self):
        super().__init__()
        self.title("만들오토V1.0")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=4)

        self.canvas = Canvas(self, width=400, height=225)
        self.canvas.grid(row=0, column=0, columnspan=2, sticky="w")

        for idx, k in enumerate(slot.keys()):
            Checkbutton(self, text=k, command=lambda text=k: self.toggle_run(text)).grid(row=idx+1, column=0, sticky="w")
            Label(self, text="", name=k).grid(row=idx+1, column=1, sticky="w")

        self.cam = dxcam.create(output_color="BGR")
        self.cam.start()
        self.update()

    def update(self):
        if app_data["capture"] == "fullscreen":
            frame = self.cam.get_latest_frame()
        else:
            x1, y1, x2, y2 = get_win_size(target_hwnd)
            frame = self.cam.get_latest_frame()[y1:y2, x1:x2]
        
        if resize:
            frame = cv2.resize(frame, dsize=(resize[0], resize[1]), interpolation=cv2.INTER_AREA)

        thumbnail = cv2.resize(frame, dsize=(400,225), interpolation=cv2.INTER_AREA)
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, image=self.photo, anchor=NW)

        for name in slot.keys():
            if slot[name]["type"] == "timer":
                if slot[name]["run"] == True:
                    if slot[name]["cooling"] == False:
                        key = slot[name]["key"]
                        cooltime = float(slot[name]["cooltime"])
                        cool_run(name, cooltime)
                        send_keys(key, frame)

            elif slot[name]["type"] == "hp":
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
                self.nametowidget(name).configure(text=f"인식값: {hp} / 사용구간: {min_hp}~{max_hp}")
                
                if hp >= min_hp and hp <= max_hp and slot[name]["cooling"] == False and slot[name]["run"] == True:
                    cool_run(name, cooltime)
                    send_keys(key, frame)

            elif slot[name]["type"] == "img":
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
                self.nametowidget(name).configure(text=f"인식값: {max_val} / 실행값: {thres}")

                if found == True and slot[name]["cooling"] == False and slot[name]["run"] == True:
                    cool_run(name, cooltime)
                    send_keys(key, frame)

        self.after(int(1000/fps), self.update)

    def toggle_run(self, name):
        slot[name]["run"] = not slot[name]["run"]

app = MainWindow()
app.mainloop()