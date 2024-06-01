from textual.app import App
from textual.widgets import Header, Footer, Static, Button, Log
from textual.containers import Horizontal
from textual.binding import Binding
from datetime import datetime
import json
import numpy as np
import cv2
import os
import platform
import requests
import threading
import time

frame_curr = None
frame_prev = None
#x1, y1, x2, y2 = 0, 0, 0, 0

# if platform.system() == "Windows":
#     import win32gui
#     # Get window handle
#     app_hwnd = win32gui.GetForegroundWindow()
#     # Set window size and position(Windows only. Right side)
#     win32gui.MoveWindow(app_hwnd, 0, 0, 400, 600, True)

def exit_app(msg):
    print(msg)
    time.sleep(2)
    os._exit(1)

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def load_img(path):
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img

# def get_win_list():
#     def callback(hwnd, hwnd_list: list):
#         title = win32gui.GetWindowText(hwnd)
#         if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
#             hwnd_list.append((title, hwnd))
#         return True
#     output = []
#     win32gui.EnumWindows(callback, output)
#     return output

# def find_window(target):
#     win_ary = get_win_list()
#     for win in win_ary:
#         if target in win[0]:
#             target_text = win[0]
#             target_hwnd = win[1]
#     return target_hwnd, target_text

# def get_win_size(hwnd):
#     left, top, right, bottom = win32gui.GetWindowRect(hwnd)
#     return left, top, right, bottom

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
    #HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
    hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
    hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
    hpThres = cv2.threshold(hpBlur, thres_min, 255, cv2.THRESH_BINARY)[1]
    #배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
    hpPoint = np.flip(hpThres).argmax()
    hpPoint = 100 if hpPoint >= hpThres.shape[1] else int((1-(np.flip(hpThres).argmax() / hpThres.shape[1])) * 100)
    return hpPoint

def tele_send_msg(msg):
    try:
        token = userdata["app"]["telegram_token"]
        chat_id = userdata["app"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
        requests.get(url)
    except:
        print("텔레그램 메세지 보내기 실패.")

def tele_send_photo(filename, caption):
    try:
        token = userdata["app"]["telegram_token"]
        chat_id = userdata["app"]["telegram_chat_id"]
        data = {"chat_id": chat_id, "caption": caption}
        url = f"https://api.telegram.org/bot{token}/sendphoto?chat_id={chat_id}"
        with open(filename, "rb") as f:
            requests.post(url, data=data, files={"photo": f})
    except:
        print("텔레그램 사진 보내기 실패")

def send_keys(keys, frame):
    key_ary = keys.split(",")
    for key in key_ary:
        if "-" in key:
            time.sleep(float(key[1:]))
        elif "!" in key:
            msg = key[1:]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
        elif "@" in key:
            msg = key[1:]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()
        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        elif "click" in key:
            #click(123;456)
            mx = int(key.split("(")[1].split(";")[0])
            my = int(key.split("(")[1].split(";")[1][:-1])
            if app.hwnd:
                mx, my = mx + x1, my + y1
            requests.get(f"{userdata['app']['input_url']}click({mx};{my})")
            time.sleep(0.2)
        else:
            requests.get(f"{userdata['app']['input_url']}{key}")
            time.sleep(0.2)

def cool_run(slot, key, sec):
    userdata[slot][key]["cooling"] = True
    threading.Timer(sec, cool_down, [slot, key]).start()

def cool_down(slot, key):
    userdata[slot][key]["cooling"] = False

class MyButton(Static):
    def compose(self):
        yield Horizontal(Button(self.renderable, variant="default"), Static("Text\nText2\nText3"))

class MyApp(App):

    BINDINGS =[
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="c", action="clear_all", description="All off")
    ]

    def on_mount(self):
        capture_target = userdata["app"]["capture_target"]
        if capture_target == "fullscreen":
            self.hwnd = False
            self.write_log("Capture: Fullscreen")
            self.title = "Fullscreen"

        # else:
        #     self.hwnd, text = find_window(capture_target)
        #     self.write_log(f"Capture: {text}")
        #     self.title = text


        if isinstance(userdata["app"]["resize"], list):
            self.resize = userdata["app"]["resize"]
        else:
            self.resize = False
        self.write_log(f"Resize: {self.resize}")

        if userdata.get('timer'):
            for idx, slot in enumerate(userdata['timer'].keys()):
                key = userdata['timer'][slot]['key']
                cooltime = userdata['timer'][slot]['cooltime']
                self.query_one(f"#timer{idx}").children[0].children[1].renderable = f"{'Key'.center(10)}: {key}\n{'Cooltime'.center(10)}: {cooltime}"

        if userdata.get('hpslot'):
            for idx, slot in enumerate(userdata['hpslot'].keys()):
                key = userdata['hpslot'][slot]['key']
                min_hp, max_hp = userdata['hpslot'][slot]['hp_range']
                self.query_one(f"#hpslot{idx}").children[0].children[1].renderable = f"{'Key'.center(10)}: {key}\n{'Range'.center(10)}: {min_hp}% ~ {max_hp}%\n{'Value'.center(10)}:"

        if userdata.get('imgslot'):
            for idx, slot in enumerate(userdata['imgslot'].keys()):
                key = userdata['imgslot'][slot]['key']
                thres = userdata['imgslot'][slot]['thres']
                self.query_one(f"#imgslot{idx}").children[0].children[1].renderable = f"{'Key'.center(10)}: {key}\n{'Threshold'.center(10)}: {thres}\n{'Value'.center(10)}:"
        
        self.write_log("앱을 시작합니다.")
        self.set_interval(0.2, self.capture_loop)
        self.set_interval(0.1, self.control_loop)

    def compose(self):
        yield Header(show_clock=True)
        yield Log(id="log")

        if userdata.get('timer'):
            for idx, slot in enumerate(userdata['timer'].keys()):
                yield MyButton(f"{slot}", id=f"timer{idx}")

        if userdata.get('hpslot'):
            for idx, slot in enumerate(userdata['hpslot'].keys()):
                yield MyButton(f"{slot}", id=f"hpslot{idx}")
                
        if userdata.get('imgslot'):
            for idx, slot in enumerate(userdata['imgslot'].keys()):
                yield MyButton(f"{slot}", id=f"imgslot{idx}")
        yield Footer()

    def on_button_pressed(self, event):
        variant = event.button.variant
        event.button.variant = "success" if variant == "default" else "default"

    def write_log(self, msg):
        clock = datetime.now().time()
        self.query_one("#log").write_line(f"[{clock:%T}] {msg}")

    def action_clear_all(self):
        for btn in self.query("Button"):
            btn.variant = "default"
        self.write_log("All off")

    def capture_loop(self):
        global frame_curr, frame_prev
        ret, frame_curr = cap.read()
        if ret == False:
            frame_curr = frame_prev.copy()
        else:
            frame_prev = frame_curr.copy()

    def control_loop(self):
        global x1, y1, x2, y2
        frame = frame_curr.copy()
        if self.hwnd:
            x1, y1, x2, y2 = get_win_size(self.hwnd)
            frame = frame[y1:y2, x1:x2]
        if self.resize:
            frame = cv2.resize(frame, dsize=(self.resize[0], self.resize[1]), interpolation=cv2.INTER_AREA)

        if userdata.get('timer'):
            for idx, slot in enumerate(userdata['timer'].keys()):
                if self.query_one(f"#timer{idx}").children[0].children[0].variant == "success":
                    if userdata['timer'][slot]['cooling'] == False:
                        key = userdata['timer'][slot]['key']
                        cooltime = userdata['timer'][slot]['cooltime']
                        cool_run("timer", slot, cooltime)
                        self.write_log(f"Run: {slot}")
                        send_keys(key, frame)
        
        if userdata.get('hpslot'):
            for idx, slot in enumerate(userdata['hpslot'].keys()):
                if self.query_one(f"#hpslot{idx}").children[0].children[0].variant == "success":
                    roi_x1, roi_y1, roi_x2, roi_y2 = userdata['hpslot'][slot]['roi']
                    roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                    thres = userdata['hpslot'][slot]['thres']
                    key = userdata['hpslot'][slot]['key']
                    cooltime = userdata['hpslot'][slot]['cooltime']
                    min_hp, max_hp = userdata['hpslot'][slot]['hp_range']
                    hp = calc_hp(roi, thres)
                    self.query_one(f"#hpslot{idx}").children[0].children[1].update(f"{'Key'.center(10)}: {key}\n{'Range'.center(10)}: {min_hp}% ~ {max_hp}%\n{'Value'.center(10)}: {hp}%")
                    if userdata['hpslot'][slot]['cooling'] == False:
                        if hp >= min_hp and hp <= max_hp:        
                            cool_run("hpslot", slot, cooltime)
                            self.write_log(f"Run: {slot}")
                            send_keys(key, frame)


        if userdata.get('imgslot'):
            for idx, slot in enumerate(userdata['imgslot'].keys()):
                if self.query_one(f"#imgslot{idx}").children[0].children[0].variant == "success":
                    roi_x1, roi_y1, roi_x2, roi_y2 = userdata['imgslot'][slot]['roi']
                    key = userdata['imgslot'][slot]['key']
                    cooltime = userdata['imgslot'][slot]['cooltime']
                    thres = userdata['imgslot'][slot]['thres']
                    dest_img = frame.copy()
                    roi = dest_img[roi_y1:roi_y2, roi_x1:roi_x2]
                    _x, _y, _w, _h, max_val = find_img(roi, img_ary[idx])
                    self.query_one(f"#imgslot{idx}").children[0].children[1].update(f"{'Key'.center(10)}: {key}\n{'Threshold'.center(10)}: {thres}\n{'Value'.center(10)}: {str(max_val)}")
                    if userdata['imgslot'][slot]['cooling'] == False:
                        if max_val >= thres:
                            cool_run("imgslot", slot, cooltime)
                            self.write_log(f"Run: {slot}")
                            send_keys(key, frame)


# capture folder
if not os.path.isdir("capture"):
    os.system("mkdir capture")

userdata = load_json("userdata.json")

# Stream server check
cap = cv2.VideoCapture(userdata["app"]["stream_url"])
ret, frame_curr = cap.read()
if ret == False: exit_app("Stream server connection failed.")
frame_prev = frame_curr.copy()

# Input server check
try:
    requests.get(f"{userdata['app']['input_url']}i")
except: exit_app("Input server connection failed.")

img_ary = []
if userdata.get("imgslot"):
    for slot in userdata["imgslot"].keys():
        filename = userdata["imgslot"][slot]["img_name"]
        img_ary.append(load_img(filename))

app = MyApp(css_path="app.tcss")
app.run()
