from textual.app import App
from textual.widgets import Header, Footer, Switch, Static, Button, Log, Input
from textual.containers import Horizontal, Vertical
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


if platform.system() == "Windows":
    import win32gui
    # Get window handle
    #app_hwnd = win32gui.GetForegroundWindow()
    
    # Set window size and position(Windows only. Right side)
    # win32gui.MoveWindow(app_hwnd, 0, 0, 400, 600, True)

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def load_img(path):
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img

def tele_send_msg(msg):
    try:
        token = app_data["token"]
        chat_id = app_data["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
        requests.get(url)
    except:
        print("텔레그램 메세지 보내기 실패.")

def tele_send_photo(filename, caption):
    try:
        token = app_data["token"]
        chat_id = app_data["chat_id"]
        data = {"chat_id": chat_id, "caption": caption}
        url = f"https://api.telegram.org/bot{token}/sendphoto?chat_id={chat_id}"
        with open(filename, "rb") as f:
            requests.post(url, data=data, files={"photo": f})
    except:
        print("텔레그램 사진 보내기 실패")

def send_keys(keys, inform=False):
    key_ary = keys.split(",")
    for key in key_ary:
        if "-" in key:
            t = float(key[1:])
            time.sleep(t)
        elif "!" in key:
            msg = key[1:]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
        elif "@" in key:
            msg = key[1:]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()
        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        else:
            if inform: print(f"{time.strftime('%x %X')} - {key}")
            try: ser.write(key.encode())
            except: pass
    return

def cool_run(type, idx, sec):
    global timer, hpslot, imgslot
    if type == "timer":
        timer[idx]["cooling"] = True
    elif type == "hpslot":
        hpslot[idx]["cooling"] = True
    elif type == "imgslot":
        imgslot[idx]["cooling"] = True
    threading.Timer(sec, cool_down, [type, idx]).start()
    return

def cool_down(type, idx):
    global timer, hpslot, imgslot
    if type == "timer":
        timer[idx]["cooling"] = False
    elif type == "hpslot":
        hpslot[idx]["cooling"] = False
    elif type == "imgslot":
        imgslot[idx]["cooling"] = False
    return

class MyButton(Static):
    def compose(self):
        yield Horizontal(Button(self.renderable, variant="default"), Static("Text\nText2\nText3"))

class MyApp(App):

    BINDINGS =[
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="c", action="clear_all", description="All off")
    ]

    def on_mount(self):
        self.title = "Mandloh app"
        #for timer in userdata['timer'].keys():
            
        """
        for idx, widget in enumerate(self.query(".timer Horizontal")):
            widget.children[1].renderable= f"{'Key'.ljust(10)}: {timer[idx]['key']}\n{'Cooltime'.ljust(10)}: {timer[idx]['cooltime']}"

        for idx, widget in enumerate(self.query(".hpslot Horizontal")):
            widget.children[1].renderable= f"{'Key'.ljust(10)}: {hpslot[idx]['key']}\n{'Range'.ljust(10)}: {hpslot[idx]['min_hp']}% ~ {hpslot[idx]['max_hp']}%\n{'Value'.ljust(10)}: Undefined"

        for idx, widget in enumerate(self.query(".imgslot Horizontal")):
            widget.children[1].renderable= f"{'Key'.ljust(10)}: {hpslot[idx]['key']}\n{'Threshold'.ljust(10)}: {imgslot[idx]['thres']}%\n{'Value'.ljust(10)}: Undefined"
        """
        self.write_log("앱을 시작합니다.")

    def compose(self):
        yield Header(show_clock=True)
        yield Log(id="log")
        """
        for t in timer:
            yield MyButton(f"{t['label']}", classes="timer")
        for hp in hpslot:
            yield MyButton(f"{hp['label']}", classes="hpslot")
        for img in imgslot:
            yield MyButton(f"{img['label']}", classes="imgslot")
        """
        if userdata.get('timer'):
            for slot in userdata['timer'].keys():
                yield MyButton(f"{slot}", classes="timer")

        if userdata.get('hpslot'):
            for slot in userdata['hpslot'].keys():
                yield MyButton(f"{slot}", classes="timer")
                
        if userdata.get('imgslot'):
            for slot in userdata['imgslot'].keys():
                yield MyButton(f"{slot}", classes="timer")
        
        yield Footer()

    def on_button_pressed(self, event):
        variant = event.button.variant
        event.button.variant = "success" if variant == "default" else "default"
        self.write_log(stream_url)

    def write_log(self, msg):
        clock = datetime.now().time()
        self.query_one("#log").write_line(f"{clock:%T}: {msg}")

    def action_clear_all(self):
        for btn in self.query("Button"):
            btn.variant = "default"
        self.write_log("All off")



# capture folder
if not os.path.isdir("capture"):
    os.system("mkdir capture")

"""
app_data = load_json("data/app.json")
stream_url = app_data["stream_url"]
input_url = app_data["input_url"]
resize_1280x720 = app_data["resize_1280x720"]
"""

userdata = load_json("userdata.json")

# Server check
#res = requests.get(f"{userdata['stream_url']}check")


"""
jsons = [j for j in os.listdir("data") if ".json" in j]
for j in jsons:
    data = load_json(f"data/{j}")
    data["label"] = j.split(".")[0]
    data["cooling"] = False
    type = data["type"]
    if type == "timer":
        timer.append(data)
    elif type == "hpslot":
        hpslot.append(data)
    elif type == "imgslot":
        imgslot.append(data)

img_ary = [load_img(f'data/{i["img_name"]}') for i in imgslot]
"""


app = MyApp(css_path="app.tcss")
app.run()
