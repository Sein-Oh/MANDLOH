from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Log
from datetime import datetime
import cv2
import numpy as np
import os
import threading
import time
import requests
import sys

fps = 4

if sys.platform == "win32":
    import dxcam
    import serial
    import win32gui
    import mouse


if not os.path.isdir("capture"):
    os.system("mkdir capture")


def read_txt(path):
    with open(path, "r", encoding="UTF-8") as file:
        raw_file = file.readlines()
        file = list(map(lambda s: s.strip(), raw_file))
        file = [f for f in file if f] #빈칸 제거용
        return file
    

def convert_data(data_path, dict_data):
    for data in read_txt(data_path):
        title, value = list(map(lambda s: s.strip(), data.split(":")))
        dict_data[title] = value


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
    cooling[key] = False


def cool_run(key, sec):
    cooling[key] = True
    threading.Timer(sec, cool_down, args=[key]).start()


def tele_send_msg(msg):
    try:
        token = app_data["telegram token"]
        chat_id = app_data["telegram chat id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
        requests.get(url)
    except:
        app.write_log("텔레그램 메세지 보내기 실패.")

def tele_send_photo(filename, caption):
    try:
        token = app_data["telegram token"]
        chat_id = app_data["telegram chat id"]
        data = {"chat_id": chat_id, "caption": caption}
        url = f"https://api.telegram.org/bot{token}/sendphoto?chat_id={chat_id}"
        with open(filename, "rb") as f:
            requests.post(url, data=data, files={"photo": f})
    except:
        app.write_log("텔레그램 사진 보내기 실패")


def send_keys(keys, frame):
    key_ary = keys.split(" ")
    for key in key_ary:
        if "-" in key:
            time.sleep(float(key[1:]))
        elif "," in key:
            mx, my = list(map(int, key.split(",")))
            mouse.move(mx, my, duration=0.2)
            #Click
        elif "noti" in key:
            #noti-msg
            msg = key[1:]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
        elif "photo" in key:
            #photo-caption
            msg = key[1:]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()
        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        else:
            ser.write(key.encode())

app_data = {}
convert_data("App.txt", app_data)

run = {}
cooling = {}
img = {}
values = {}

timer = {}
hpslot = {}
imgslot = {}

txt_ary = [j for j in os.listdir("data") if ".txt" in j]
for txt in txt_ary:
    name = txt.split(".")[0]
    temp = {}

    run[name] = False
    cooling[name] = False

    convert_data(f"data/{txt}", temp)
    if temp["type"] == "timer":
        timer[name] = temp.copy()
    elif temp["type"] == "hp":
        hpslot[name] = temp.copy()
    elif temp["type"] == "img":
        imgslot[name] = temp.copy()
        img[name] = load_img(f'data/{imgslot[name]["img"]}')

cam = dxcam.create(output_color="BGR")
cam.start(target_fps=fps)

ser = serial.Serial(port=app_data["arduino port"], baudrate=9600)

class TimerSlot(Static):
    play = reactive(False)
    def compose(self):
        yield Button(self.renderable, classes="run", variant="default")
        yield Static("", classes="text")

    def on_button_pressed(self, event):
        self.play = not self.play
        self.query_one(".run").variant = "success" if self.play else "default"
        run[str(self.renderable)] = self.play


class HpSlot(Static):
    play = reactive(False)
    def compose(self):
        yield Button(self.renderable, id="run", classes="run", variant="default")
        yield Static("", classes="text")
        yield Button("Check", classes="check", variant="primary")
    
    def on_button_pressed(self, event):
        if event.button.id == "run":
            self.play = not self.play
            self.query_one(".run").variant = "success" if self.play else "default"
            run[str(self.renderable)] = self.play


class ImgSlot(Static):
    play = reactive(False)
    def compose(self):
        yield Button(self.renderable, id="run", classes="run", variant="default")
        yield Static("", classes="text")
        yield Button("Check", classes="check", variant="primary")
    
    def on_button_pressed(self, event):
        if event.button.id == "run":
            self.play = not self.play
            self.query_one(".run").variant = "success" if self.play else "default"
            run[str(self.renderable)] = self.play


class MyApp(App):
    BINDINGS =[
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="c", action="clear_all", description="All off")
    ]
    def compose(self):
        yield Header(show_clock=True)
        yield Log(id="log")
        for idx, key in enumerate(timer.keys()):
            yield TimerSlot(key, classes="t"*(idx+1))

        for idx, key in enumerate(hpslot.keys()):
            yield HpSlot(key, classes="h"*(idx+1))

        for idx, key in enumerate(imgslot.keys()):
            yield ImgSlot(key, classes="i"*(idx+1))
        yield Footer()

    def on_mount(self):
        if app_data["capture"] != "fullscreen":
            self.target_hwnd, target_text = find_window(app_data["capture"])
            self.write_log(f"Capture : {target_text}")
        else:
            self.write_log("Capture : fullscreen")

        self.resize = list(map(int, app_data["resize"].split())) if app_data["resize"] else False
        self.write_log(f"Resize : {self.resize}")

        for idx, key in enumerate(timer.keys()):
            info = f'Key : {timer[key]["key"]}\nCooltime : {timer[key]["cooltime"]}'
            self.query_one(f".{'t'*(idx+1)}  Static").update(renderable=info)
        self.set_interval(1/fps, self.loop)


    def write_log(self, msg):
        clock = datetime.now().time()
        self.query_one("#log").write_line(f"[{clock:%T}] {msg}")


    def action_clear_all(self):
        for key in run.keys():
            run[key] = False

        for slot in self.query("TimerSlot"):
            slot.play = False
            slot.query_one(".run").variant = "default"

        for slot in self.query("HpSlot"):
            slot.play = False
            slot.query_one(".run").variant = "default"

        for slot in self.query("ImgSlot"):
            slot.play = False
            slot.query_one(".run").variant = "default"

        self.write_log("All off")


    def loop(self):
        if app_data["capture"] == "fullscreen":
            frame = cam.get_latest_frame()
        else:
            x1, y1, x2, y2 = get_win_size(self.target_hwnd)
            frame = cam.get_latest_frame()[y1:y2, x1:x2]
        if self.resize:
            frame = cv2.resize(frame, dsize=(self.resize[0], self.resize[1]), interpolation=cv2.INTER_AREA)

        for idx, key in enumerate(timer.keys()):
            if run[key] == True and cooling[key] == False:
                cool_run(key, float(timer[key]["cooltime"]))
                send_keys(timer[key]["key"], frame)

        for idx, key in enumerate(hpslot.keys()):
            if run[key] == True:
                x1 = int(hpslot[key]["x1"])
                y1 = int(hpslot[key]["y1"])
                x2 = int(hpslot[key]["x2"])
                y2 = int(hpslot[key]["y2"])
                thres = float(hpslot[key]["threshold"])
                min_hp = int(hpslot[key]["min range"])
                max_hp = int(hpslot[key]["max range"])
                roi = frame[y1:y2, x1:x2]
                hp, thres_img = calc_hp(roi, thres)
                info = f'Key : {hpslot[key]["key"]}\nRange : {min_hp}~{max_hp}\nValue : [red]{hp}[/red]'
                self.query_one(f".{'h'*(idx+1)}  Static").update(renderable=info)

                if hp >= min_hp and hp <= max_hp and cooling[key] == False:
                    cool_run(key, float(hpslot[key]["cooltime"]))
                    send_keys(hpslot[key]["key"], frame)

        for idx, key in enumerate(imgslot.keys()):
            if run[key] == True:
                x1 = int(imgslot[key]["x1"])
                y1 = int(imgslot[key]["y1"])
                x2 = int(imgslot[key]["x2"])
                y2 = int(imgslot[key]["y2"])
                thres = float(imgslot[key]["threshold"])
                roi = frame[y1:y2, x1:x2]
                _x, _y, _w, _h, max_val = find_img(roi, img[key])
                found = True if max_val >= thres else False
                info = f"Threshold : {thres}\nFound : {max_val}"
                self.query_one(f".{'i'*(idx+1)}  Static").update(renderable=info)

                if found == True and cooling[key] == False:
                    cool_run(key, float(imgslot[key]["cooltime"]))
                    send_keys(imgslot[key]["key"], frame)


app = MyApp(css_path="app.tcss")
app.run()
