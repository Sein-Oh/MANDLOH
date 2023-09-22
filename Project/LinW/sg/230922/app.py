import json
import dxcam
import cv2
import numpy as np
import PySimpleGUI as sg
import win32gui
import time
import threading
import sys
import mouse

def close_window():
    print("설정에 오류가 있습니다. 3초후 앱이 종료됩니다.")
    time.sleep(3)
    window.close()
    sys.exit()

def refresh_window():
    global window_hwnd, x1, y1, x2, y2
    param = load_data("params.json")
    update_label(param)
    window_hwnd = find_window(param["target_window"])[1]
    if window_hwnd is None: close_window()
    x1, y1, x2, y2 = get_win_size(window_hwnd)

def load_data(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def check_int(key):
    try:
        param[key] = int(param[key])
        return True
    except:
        print(f"{key} : {param[key]} 입력값 오류.")
        return False

def check_float(key):
    try:
        param[key] = float(param[key])
        return True
    except:
        print(f"{key} : {param[key]} 입력값 오류.")
        return False

def check_img(key):
    img = cv2.imread(param[key])
    if img is None:
        print(f"{key} : {param[key]} 이미지파일 오류.")
        return False
    else:
        img_dict[key.split("_")[0]] = img
        return True

def check_param(slot):
    data = [p for p in param.keys() if slot in p and "label" not in p]
    for key in data:
        if "_roi" in key or "_hp" in key: #int
            if check_int(key) == False: return False
        if "hp" in key and "thres" in key: #int
            if check_int(key) == False: return False
        if "img" in key and "thres" in key: #float
            if check_float(key) == False: return False
        if "_cool" in key: #float
            if check_float(key) == False: return False
        if "_path" in key: #imf file
            if check_img(key) == False: return False
    return True

def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

def find_window(title):
    win_list = get_win_list()
    result = []
    for win in win_list:
        if title in win[0]:
            result.append(win)
    if len(result) < 1:
        print("윈도우를 찾을 수 없습니다.")
        return
    elif len(result) > 1:
        print("윈도우가 2개 이상입니다. 첫 번째 윈도우로 실행합니다.")
    return result[0]

def update_label(param):
    for i in range(1,6):
        timer_key = f"timer{i}"
        hpslot_key = f"hpslot{i}"
        imgslot_key = f"imgslot{i}"
        window[timer_key].update(text=f"{param[f'{timer_key}_label']}")
        window[hpslot_key].update(text=f"{param[f'{hpslot_key}_label']}")
        window[imgslot_key].update(text=f"{param[f'{imgslot_key}_label']}")
    return

def stop_all():
    for i in range(1,6):
        timer_key = f"timer{i}"
        hpslot_key = f"hpslot{i}"
        imgslot_key = f"imgslot{i}"
        window[timer_key].update(value=False)
        window[hpslot_key].update(value=False)
        window[imgslot_key].update(value=False)
    return

def cool_run(key, sec):
    global cool_dict
    cool_dict[key] = True
    threading.Timer(sec, cool_down, [key]).start()

def cool_down(key):
    global cool_dict
    cool_dict[key] = False

def find_img(background, target):
    h, w, _ = target.shape
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    return x, y, w, h, max_val

def calc_hp(img_hp, thres_min=210):
    #HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
    hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
    hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
    hpThres = cv2.threshold(hpBlur, thres_min, 255, cv2.THRESH_BINARY)[1]
    hpThres_img = cv2.cvtColor(hpThres, cv2.COLOR_GRAY2BGR)
    #배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
    hpPoint = np.flip(hpThres).argmax()
    hpPoint = 100 if hpPoint >= hpThres.shape[1] else int((1-(np.flip(hpThres).argmax() / hpThres.shape[1])) * 100)
    return hpPoint, hpThres_img

def capture_loop():
    global frame
    while True:
        frame = cam.get_latest_frame()[y1:y2, x1:x2]
        # capture_dict["frame"] = cam.get_latest_frame()[y1:y2, x1:x2]

        if window["show_mouse"].get() == True:
            mouse_x, mouse_y = mouse.get_position()
            mouse_x, mouse_y = mouse_x - x1, mouse_y - y1
            print(f"x : {mouse_x}, y : {mouse_y}")

        for slot in hpslot_ary:
            if window[slot].get() == True:
                roi_x1 = param[f"{slot}_roi_x1"]
                roi_y1 = param[f"{slot}_roi_y1"]
                roi_x2 = param[f"{slot}_roi_x2"]
                roi_y2 = param[f"{slot}_roi_y2"]
                thres = param[f"{slot}_thres"]
                # hp_img_dict[slot] = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                # capture_dict[slot] = capture_dict["frame"][roi_y1:roi_y2, roi_x1:roi_x2]

def action_loop():
    while True:
        # timer
        for timer in timer_ary:
            if window[timer].get() == True and cool_dict[timer] == False:
                inp = param[f"{timer}_key"]
                cool = param[f"{timer}_cool"]
                cool_run(timer, cool)
                print(f"{timer} run!!")

        # hpslot
        # for slot in hpslot_ary:
        #     if window[slot].get() == True and cool_dict[slot] == False:
        #         inp = param[f"{slot}_key"]
        #         cool = float(param[f"{slot}_cool"])
        #         min_hp = int(param[f"{slot}_min_hp"])
        #         max_hp = int(param[f"{slot}_max_hp"])


        time.sleep(0.2)

frame_timer = [
    [sg.Checkbox("", key="timer1", enable_events=True)],
    [sg.Checkbox("", key="timer2", enable_events=True)],
    [sg.Checkbox("", key="timer3", enable_events=True)],
    [sg.Checkbox("", key="timer4", enable_events=True)],
    [sg.Checkbox("", key="timer5", enable_events=True)],
]

frame_hpslot = [
    [sg.Checkbox("", key="hpslot1", enable_events=True)],
    [sg.Checkbox("", key="hpslot2", enable_events=True)],
    [sg.Checkbox("", key="hpslot3", enable_events=True)],
    [sg.Checkbox("", key="hpslot4", enable_events=True)],
    [sg.Checkbox("", key="hpslot5", enable_events=True)],
]

frame_imgslot = [
    [sg.Checkbox("", key="imgslot1", enable_events=True)],
    [sg.Checkbox("", key="imgslot2", enable_events=True)],
    [sg.Checkbox("", key="imgslot3", enable_events=True)],
    [sg.Checkbox("", key="imgslot4", enable_events=True)],
    [sg.Checkbox("", key="imgslot5", enable_events=True)],
]

layout = [
    [
        sg.Button("전체중지"),
        sg.Button("새로고침"),
        sg.Checkbox("캡처확인", key="show_capture", enable_events=True),
        sg.Checkbox("마우스 좌표확인", key="show_mouse"),
    ],
    [sg.Frame("타이머", frame_timer, size=(100,170)), sg.Frame("타이머", frame_hpslot, size=(100,170)), sg.Frame("타이머", frame_imgslot, size=(100,170))],
    # [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]
window = sg.Window("앱", layout, finalize=True)

img_dict = {}
hp_img_dict = {}
capture_dict = {}
cool_dict = {}
timer_ary = []
hpslot_ary = []
imgslot_ary = []
for i in range(1,6):
    cool_dict[f"timer{i}"] = False
    cool_dict[f"hpslot{i}"] = False
    cool_dict[f"imgslot{i}"] = False
    timer_ary.append(f"timer{i}")
    hpslot_ary.append(f"hpslot{i}")
    imgslot_ary.append(f"imgslot{i}")

print("파라메터 확인...", end="")
try:
    param = load_data("params.json")
    update_label(param)
except: close_window()
print("완료.")

print("윈도우 확인...", end="")
window_hwnd = find_window(param["target_window"])[1]
x1, y1, x2, y2 = get_win_size(window_hwnd)
if window_hwnd is None: close_window()
print("완료.")

# 캡처 설정 및 시작
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=5)
frame = cam.get_latest_frame()
# capture_dict["frame"] = cam.get_latest_frame()
# threading.Thread(target=capture_loop, daemon=True).start()
# threading.Thread(target=action_loop, daemon=True).start()

while True:
    event, values = window.read(timeout=0.2)

    if event == sg.WINDOW_CLOSED or event == "종료하기":
        break
    
    elif event == "새로고침":
        refresh_window()
        print("데이터를 새로고침 합니다.")

    elif event == "전체중지":
        stop_all()
        print("모든 기능을 중지합니다.")

    elif "timer" in event or "slot" in event:
        label = param[f"{event}_label"]
        if window[event].get() == True:
            if check_param(event) == False:
                window[event].update(value=False)
            else:
                refresh_window()
                print(f"{label} 기능을 사용합니다.")
        else: print(f"{label} 기능을 중지합니다.")

window.close()