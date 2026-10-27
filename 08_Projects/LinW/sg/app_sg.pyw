import PySimpleGUI as sg
import json
import os
import cv2
import numpy as np
import time
import threading
import image_processing
import window_control
from arduino_serial import Serial
from capture import Capture
from telegram import Tele

sg.theme("Default1")
cb_size = (6,None)

def get_data():
    new_param = {}
    for key in default_param.keys():
        new_param[key] = window[key].get()
    return new_param

def load_data(filename="userdata.json"):
    with open(filename, "r") as file:
        return json.load(file)

def update_data(data):
    for key in data.keys():
        window[key].update(data[key])

def save_data(data, filename="userdata.json"):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
    print("현재 설정을 저장했습니다.")

def coolRun(key, sec):
    global coolTime
    coolTime[key] = True
    threading.Timer(sec, coolDown, [key]).start()

def coolDown(key):
    global coolTime
    coolTime[key] = False

# 이미지 찾기 함수
def find_img(background, target, threshold):
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    res = np.where(res>=threshold) # res에서 threshold보다 큰 값만 취한다.
    point = []
    for pt in zip(*res[::-1]):
        point.append(pt)
    print(point)
    return len(point) # 찾음여부만 확인하기 위해 길이로 리턴한다.

def loop():
    global hpPoint, party, img
    while True:
        screen_img = cap.frame
        full_img = screen_img[y1:y2, x1:x2]
        resized_img = cv2.resize(full_img, (1280,720), interpolation=cv2.INTER_AREA)
        
        #HP 잘라내기
        img_hp = resized_img[hp_y:hp_y+hp_h, hp_x:hp_x+hp_w]  # y1:y2,x1:x2
        window["img_hp"].update(data=cv2.imencode(".png", img_hp)[1].tobytes()) # 이미지 업데이트

        #HP 계산
        hpPoint = image_processing.calc_hp(img_hp)
        window["lbl_hp"].update("HP: {}%".format(hpPoint)) # 라벨 업데이트

        #파티원 체력 잘라내기
        img_p1 = resized_img[p1_y:p1_y+p1_h, p1_x:p1_x+p1_w]
        img_p2 = resized_img[p2_y:p2_y+p2_h, p2_x:p2_x+p2_w]
        img_p3 = resized_img[p3_y:p3_y+p3_h, p3_x:p3_x+p3_w]

        hp_p1 = image_processing.calc_hp(img_p1, 150)
        hp_p2 = image_processing.calc_hp(img_p2, 150)
        hp_p3 = image_processing.calc_hp(img_p3, 150)
        party = [hp_p1, hp_p2, hp_p3]


        #귀환
        if window["cb_home"].get() == True:
            key = window["key_home"].get()
            cool = float(window["cool_home"].get())
            hp_range = window["hp_home"].get().split(",")
            hp_min, hp_max = int(hp_range[0]), int(hp_range[1])
            if hpPoint >= hp_min and hpPoint <= hp_max and coolTime["home"] == False:
                print("귀환기능을 사용합니다.")
                coolRun("home", cool)
                cv2.imwrite(f"last_event.jpg", resized_img) # 상황 캡쳐
                ser.send(key + "," + key)
                time.sleep(0.5)
                tele.send_photo("last_event.jpg", "귀환")

        
        #타이머 처리
        timer_ary = [x for x in param if "cb_timer" in x]
        for timer in timer_ary:
            if window[timer].get() == True:
                name = timer.split("_")[1]
                key = window["key_"+name].get()
                cool = float(window["cool_"+name].get())
                if coolTime[name] == False:
                    coolRun(name, cool)
                    ser.send(key)

        #슬롯 처리
        slot_ary = [x for x in param if "cb_slot" in x]
        for slot in slot_ary:
            if window[slot].get() == True:
                name = slot.split("_")[1]
                key = window["key_"+name].get()
                cool = float(window["cool_"+name].get())
                hp_range = window["hp_"+name].get().split(",")
                hp_min, hp_max = int(hp_range[0]), int(hp_range[1])
                if hpPoint >= hp_min and hpPoint <= hp_max and coolTime[name] == False:
                    print(f"{name} 기능을 사용합니다.")
                    coolRun(name, cool)
                    ser.send(key)
                    time.sleep(0.5)


        #파티
        party_ary = ["cb_p1", "cb_p2", "cb_p3"]
        for p in party_ary:
            if window[p].get() == True:
                num = int(p[-1])
                if coolTime[f"p{num}"] == False and party[num-1] <= 85:
                    coolRun(f"p{num}", 1)
                    ser.send(f"f{num}")
                    time.sleep(0.5)

        #이미지
        img_ary = ["cb_img1", "cb_img2"]
        for img in img_ary:
            if window[img].get() == True:
                num = img[-1]
                key = window[f"key_img{num}"].get()
                cool = float(window[f"cool_img{num}"].get())
                idx = int(num) - 1
                if img_group[idx] == None:
                    full_path = window[f"path_img{num}"].get()
                    path = full_path.split("/")[-1]
                    tag = path.split("_")
                    im_x1 = int(tag[1])
                    im_x2 = int(tag[2])
                    im_y1 = int(tag[3])
                    im_y2 = int(tag[4])
                    thres = float(tag[5])
                    img_group[idx] = cv2.imread(full_path)
                    back_group[idx] = resized_img[im_y1:im_y2, im_x1:im_x2]
                    print(img_group[idx].shape)
                    print(back_group[idx].shape)

                
                res = find_img(back_group[idx], img_group[idx], thres)

        time.sleep(0.1)

hp_monitor = [
    [sg.Text("HP:미확인", key="lbl_hp", size=(10, None)), sg.Image(size=(200, 6), key="img_hp")],
    [
        sg.Checkbox("귀환", size=cb_size, enable_events=True, key="cb_home"),
        sg.Text("입력키:"), sg.Input("", size=(6,None), justification="center", key="key_home"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_home"),
        sg.Text("HP범위:"), sg.Input("", size=(6,None), justification="center", key="hp_home")
    ],
    [
        sg.Checkbox("슬롯1", size=cb_size, enable_events=True, key="cb_slot1"),
        sg.Text("입력키:"), sg.Input("", size=(6,None), justification="center", key="key_slot1"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_slot1"),
        sg.Text("HP범위:"), sg.Input("", size=(6,None), justification="center", key="hp_slot1")
    ],
    [
        sg.Checkbox("슬롯2", size=cb_size, enable_events=True, key="cb_slot2"),
        sg.Text("입력키:"), sg.Input("", size=(6,None), justification="center", key="key_slot2"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_slot2"),
        sg.Text("HP범위:"), sg.Input("", size=(6,None), justification="center", key="hp_slot2")
    ],
]

control = [
    [
        sg.Checkbox("타이머1", size=cb_size, enable_events=True, key="cb_timer1"),
        sg.Text("입력키:"), sg.Input("", size=(12,None), justification="center", key="key_timer1"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_timer1"),
    ],
    [
        sg.Checkbox("타이머2", size=cb_size, enable_events=True, key="cb_timer2"),
        sg.Text("입력키:"), sg.Input("", size=(12,None), justification="center", key="key_timer2"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_timer2"),
    ],
    [
        sg.Checkbox("타이머3", size=cb_size, enable_events=True, key="cb_timer3"),
        sg.Text("입력키:"), sg.Input("", size=(12,None), justification="center", key="key_timer3"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_timer3"),
    ],
]

party_control = [
    [
        sg.Checkbox("파티원1 힐", expand_x=True, enable_events=True, key="cb_p1"),
        sg.Checkbox("파티원2 힐", expand_x=True, enable_events=True, key="cb_p2"),
        sg.Checkbox("파티원3 힐", expand_x=True, enable_events=True, key="cb_p3"),
    ],
]

img_control_1 = [
    [
        sg.Checkbox("이미지1", size=cb_size, enable_events=True, key="cb_img1"),
        sg.Text("입력키:"), sg.Input("", size=(6,None), justification="center", key="key_img1"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_img1")
    ],
    [
        sg.Button("이미지선택", key="file_img1"),
        sg.Input("", key="path_img1", readonly=True)
    ]
]

img_control_2 = [
    [
        sg.Checkbox("이미지2", size=cb_size, enable_events=True, key="cb_img2"),
        sg.Text("입력키:"), sg.Input("", size=(6,None), justification="center", key="key_img2"),
        sg.Text("쿨타임:"), sg.Input("", size=(3,None), justification="center", key="cool_img2")
    ],
    [
        sg.Button("이미지선택", key="file_img2"),
        sg.Input("", key="path_img2", readonly=True)
    ]
]

pannel = [
    [
        sg.Button("가방열기", key="btn_inven", expand_x=True),
        sg.Button("저장", key="btn_save", expand_x=True),
        sg.Button("초기화", key="btn_reset", expand_x=True),
    ]
]

layout = [
    [sg.Frame("HP인식 활용 스마트 슬롯", hp_monitor, expand_x=True)],
    [sg.Frame("단순 타이머", control, expand_x=True)],
    [sg.Frame("파티 제어", party_control, expand_x=True)],
    [sg.Frame("이미지 슬롯1", img_control_1, expand_x=True)],
    [sg.Frame("이미지 슬롯2", img_control_2, expand_x=True)],
    [sg.Frame("설정", pannel, expand_x=True)],
    [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]

window = sg.Window("Lineage W", layout, finalize=True, location=(1300, 0))

########################################################
arduino_port = "COM9"
charactor_name = "메이커"

hpPoint = 100
hp_x, hp_y, hp_w, hp_h = 90, 32, 190, 6

party = [100, 100, 100]
p1_x, p1_y, p1_w, p1_h = 707, 604, 29, 3
p2_x, p2_y, p2_w, p2_h = 768, 604, 29, 3
p3_x, p3_y, p3_w, p3_h = 830, 604, 29, 3

tele_token = "1480350910:AAFwyDTBFcwQi7Y_iHXqPkbC4XIAPZ4x81c"
tele_id = "935941732"

resized_img = None

img_group = [None, None]
back_group = [None, None]

default_param = {
    "cb_timer1" : False,
    "key_timer1" : "3,f1,4,-",
    "cool_timer1" : "28",

    "cb_timer2" : False,
    "key_timer2" : "2",
    "cool_timer2" : "2",

    "cb_timer3" : False,
    "key_timer3" : "f",
    "cool_timer3" : "0.2",

    "cb_home" : False,
    "key_home" : "8",
    "cool_home" : "30",
    "hp_home" : "0,50",

    "cb_slot1" : False,
    "key_slot1" : "4",
    "cool_slot1" : "3",
    "hp_slot1" : "51,85",

    "cb_slot2" : False,
    "key_slot2" : "7",
    "cool_slot2" : "10",
    "hp_slot2" : "51,60",

    "cb_p1" : False,
    "cb_p2" : False,
    "cb_p3" : False,

    "cb_img1" : False,
    "key_img1" : "1",
    "cool_img1" : "3",
    "path_img1" : "-",

    "cb_img2" : False,
    "key_img2" : "8",
    "cool_img2" : "5",
    "path_img2" : "-",
}

coolTime = {
    "timer1" : False,
    "timer2" : False,
    "timer3" : False,
    "home" : False,
    "slot1" : False,
    "slot2" : False,
    "p1" : False,
    "p2" : False,
    "p3" : False,
    "img1" : False,
    "img2" : False,
}


print("게임창을 찾습니다.")
window_handle = window_control.get_lin_window(charactor_name)
x1, y1, x2, y2 = window_control.get_win_size(window_handle)

print("캡처를 준비합니다..")
cap = Capture(fps=2)

print("아두이노를 연결합니다...")
ser = Serial(port=arduino_port, baudrate=9600)

print("텔레그램을 연결합니다...")
tele = Tele(tele_token, tele_id)
# tele.send_message("리니지W 앱을 시작합니다.")

print("저장된 설정파일을 찾습니다....")
if os.path.isfile("userdata.json"):
    param = load_data("userdata.json")
else:
    print("파일이 없습니다. 기본 설정으로 시작합니다.")
    param = default_param
update_data(param)

print("앱을 시작합니다.")
time.sleep(0.2)
threading.Thread(target=loop, daemon=True).start()

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break

    elif event == "btn_save":
        new_param = get_data()
        save_data(new_param)

    elif event == "btn_reset":
        update_data(default_param)

    elif event == "btn_inven":
        window_control.set_foreground(window_handle)
        x1, y1, x2, y2 = window_control.get_win_size(window_handle)
        ser.send("i")

    elif "cb" in event:
        if window[event].get() == True:
            window_control.set_foreground(window_handle)
            x1, y1, x2, y2 = window_control.get_win_size(window_handle)

    elif "file" in event:
        path = sg.popup_get_file("이미지파일을 선택하세요.")
        print(path)
        slot = event.split("_")[-1]
        window[f"path_{slot}"].update(path)

window.close()