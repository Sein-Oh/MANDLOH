from textual.app import App
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Log
from textual.containers import Horizontal

import base64
import cv2
import numpy as np
import os
import requests
import threading
import time


######## Prepare ########
if not os.path.isdir("capture"):
    os.system("mkdir capture")


def parse_txt(path):
  with open(path, "r", encoding="utf-8") as f:
    file = f.read()

  userdata = {}
  for line in file.split("\n"):
    split_idx = line.find(":")
    key = line[:split_idx].strip()
    value = line[split_idx+1:].strip()
    userdata[key] = value
  return userdata


def load_img(path):
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img


def b64_to_cv(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(",")[1]), np.uint8), cv2.IMREAD_COLOR)


def cv_to_b64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    return str(im_b64)


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
    threading.Timer(sec, cool_down, args=(key,)).start()


def tele_send_msg(msg):
    try:
        url = f'https://api.telegram.org/bot{telegram["token"]}/sendMessage?chat_id={telegram["chat_id"]}&text={msg}'
        requests.get(url)
    except:
        print("텔레그램 메세지 보내기 실패.")


def tele_send_photo(filename, caption):
    try:
        data = {"chat_id": {telegram["chat_id"]}, "caption": caption}
        url = f'https://api.telegram.org/bot{telegram["token"]}/sendphoto?chat_id={telegram["chat_id"]}'
        with open(filename, "rb") as f:
            requests.post(url, data=data, files={"photo": f})
    except:
        print("텔레그램 사진 보내기 실패")


def send_req(url):
    requests.get(url, timeout=0.01)

def send_keys(keys, frame):
    key_ary = keys.split(" ")
    for key in key_ary:
        if "-" in key:
            time.sleep(float(key[1:]))
        elif "noti" in key:
            msg = key.split("(")[1].split(")")[0]
            threading.Thread(target=tele_send_msg, args=[msg,], daemon=True).start()
        elif "photo" in key:
            msg = key.split("(")[1].split(")")[0]
            cv2.imwrite("capture/event.jpg", frame)
            threading.Thread(target=tele_send_photo, args=["capture/event.jpg", msg,], daemon=True).start()
        elif key == "capture":
            cv2.imwrite(f"capture/{time.strftime('%y%m%d_%H%M%S')}.jpg", frame)
        elif "," in key:
            url = f'{server["input"]}/{key}'
            requests.get(url, timeout=0.01)
            # threading.Thread(target=send_req, args=(url,), daemon=True).start()
        else:
            url = f'{server["input"]}/{key}'
            requests.get(url, timeout=0.01)
            # threading.Thread(target=send_req, args=(url,), daemon=True).start()
            

######## Data parsing ########
userdata = {}
txt_ary = [j for j in os.listdir("slots") if ".txt" in j]
for txt in txt_ary:
    name = txt.split(".")[0]
    userdata[name] = parse_txt(f"slots/{txt}")

telegram = {}
server = {}
timer = {}
hp = {}
img = {}
cooling = {}
run = {}
pause = False

for data in userdata:
    if userdata[data]["type"] == "telegram":
        telegram["token"] = userdata[data]["token"]
        telegram["chat_id"] = userdata[data]["chat_id"]
    elif userdata[data]["type"] == "server":
        server["input"] = userdata[data]["input"]
        server["stream"] = userdata[data]["stream"]
    elif userdata[data]["type"] == "timer":
        timer[data] = userdata[data]
        run[data] = False
        cooling[data] = False
    elif userdata[data]["type"] == "hp":
        hp[data] = userdata[data]
        run[data] = False
        cooling[data] = False
    elif userdata[data]["type"] == "img":
        img[data] = userdata[data]
        img[data]["mat"] = load_img(f"slots/{userdata[data]['img']}")
        run[data] = False
        cooling[data] = False


use_telegram = True if "token" in telegram and "chat_id" in telegram else False
print(f"Telegram: {'Enabled' if use_telegram else 'Disabled'}")

cam = cv2.VideoCapture(server["stream"])
frame = cam.read()[1]


print("Capture start...")
print(f"Resolution : {frame.shape[1]}x{frame.shape[0]}")


def loop():
    while True:
        frame = cam.read()[1]
        if not pause:
            for idx, name in enumerate(img.keys()):
                if run[name] and not cooling[name]:
                    key = img[name]["key"]
                    cooltime = float(img[name]["cooltime"])
                    x1 = int(img[name]["x1"])
                    y1 = int(img[name]["y1"])
                    x2 = int(img[name]["x2"])
                    y2 = int(img[name]["y2"])
                    thres = float(img[name]["threshold"])
                    roi = frame[y1:y2, x1:x2]
                    _x, _y, _w, _h, max_val = find_img(roi, img[name]["mat"])
                    if max_val >= thres:
                        send_keys(key, frame)
                        cool_run(name, cooltime)
                    app.query_one(f"#img_{idx}").children[0].update(f"✅ {name} ({max_val})")
                else:
                    app.query_one(f"#img_{idx}").children[0].update(f"🟨 {name}")

            for idx, name in enumerate(hp.keys()):
                if run[name] and not cooling[name]:
                    key = hp[name]["key"]
                    cooltime = float(hp[name]["cooltime"])
                    x1 = int(hp[name]["x1"])
                    y1 = int(hp[name]["y1"])
                    x2 = int(hp[name]["x2"])
                    y2 = int(hp[name]["y2"])
                    thres = float(hp[name]["threshold"])
                    min_hp = int(hp[name]["min range"])
                    max_hp = int(hp[name]["max range"])
                    roi = frame[y1:y2, x1:x2]
                    hp_calc, thres_img = calc_hp(roi, thres)
                    if hp_calc >= min_hp and hp_calc <= max_hp:
                        send_keys(key, frame)
                        cool_run(name, cooltime)
                    app.query_one(f"#hp_{idx}").children[0].update(f"✅ {name} ({hp_calc})")
                else:
                    app.query_one(f"#hp_{idx}").children[0].update(f"🟨 {name}")

            for idx, name in enumerate(timer.keys()):
                if run[name] and not cooling[name]:
                    key = timer[name]["key"]
                    cooltime = float(timer[name]["cooltime"])
                    send_keys(key, frame)
                    cool_run(name, cooltime)



######## Textual Part ########
class Slot(Static):
    name = reactive("")
    def compose(self):
        yield Static(f"🟨 {self.renderable}")
    
    def on_mount(self):
        self.name = self.renderable
    
    def on_click(self):
        run[self.name] = not run[self.name]
        label = f"✅ {self.renderable}" if run[self.name] else f"🟨 {self.renderable}"
        self.query_one("Static").update(label)


class MyApp(App):

    def compose(self):
        yield Header(show_clock=True)
        for idx, name in enumerate(hp.keys()):
            yield Slot(name, id=f"hp_{idx}")
        for idx, name in enumerate(img.keys()):
            yield Slot(name, id=f"img_{idx}")
        for idx, name in enumerate(timer.keys()):
            yield Slot(name, id=f"timer_{idx}")

    def on_mount(self):
        # self.set_interval(0.2, loop)
        threading.Thread(target=loop, daemon=True).start()


app = MyApp()
app.run()
