
import PySimpleGUI as sg
import cv2
import dxcam
import mouse
import numpy as np
import serial
import serial.tools.list_ports as sp
import threading
import time
import win32gui
import win32com.client
from tkinter import filedialog

app_title = "GAME PATH FINDER"


# window handle로 창 앞으로 가져오기:
shell = win32com.client.Dispatch("WScript.Shell")
def set_foreground(handle):
    shell.SendKeys('%')
    win32gui.SetForegroundWindow(handle)

# 윈도우에 실행중인 모든 창의 Text, handle을 list로 반환.
def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

# window handle로 이미지 위치 및 크기 찾는 함수
def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

def update_hwnd():
    global window_ary
    window_ary = get_win_list()
    win_title_ary = [t[0] for t in window_ary]
    win_title_ary.insert(0, "전체화면")
    window["combo_window"].update(values=win_title_ary)

def input_test(value):
    msg = "OK"        
    send_key(msg, win_ignore=True)

def find_port():
    res = []
    for port, desc, hwid in sorted(sp.comports()):
        res.append(f"{port}, {desc}")
    return res

def update_port():
    list = find_port()
    window["combo_port"].update(values=list, value=list[0])
    return

def connect_port(port_info):
    global ser
    port_num = port_info.split(",")[0]
    try:
        ser = serial.Serial(port=port_num, baudrate=9600)
        print(f"{port_info}에 연결되었습니다.")
    except:
        ser = False
        print(f"{port_info}연결이 실패했습니다.")

def send_key(keys, announce=False, win_ignore=False):
    if announce == True:
        print(f"입력키 : {keys}")
    if active_hwnd == app_hwnd and win_ignore == True:
        print("앱을 선택하고 있어 입력을 무시합니다.")
        return
    
    if ser == False:
        print("아두이노가 연결되지 않았습니다.")
        return
    key_ary = keys.split(",")
    for key in key_ary:
        if "-" in key:
            t = float(key[1:])
            time.sleep(t)
        else: ser.write(keys.encode())
    return

def timer_cool_run(idx, sec):
    global timer_cool_ary
    timer_cool_ary[idx] = True
    threading.Timer(sec, timer_cool_down, [idx]).start()

def timer_cool_down(key):
    global timer_cool_ary
    timer_cool_ary[key] = False

def timer_loop():
    while True:
        for idx, slot in enumerate(timer_ary):
                if window[f"{slot}_cb_run"].get() == True:
                    key = check_str(f"{slot}_inp_key")
                    cool = check_float(f"{slot}_inp_cool")
                    if key != False and cool != False and timer_cool_ary[idx] == False:
                        timer_cool_run(idx, cool)
                        send_key(key)
                        print(key)
        time.sleep(0.1)

# 이미지찾기 함수
def find_img(background, target):
    h, w, _ = target.shape
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    return x, y, w, h, max_val

def update_frame():
    global frame
    while True:
        mouse_x, mouse_y = mouse.get_position()
        if window_select == "전체화면":
            frame = cam.get_latest_frame()
        else:
            x1, y1, x2, y2 = get_win_size(window_select_hwnd)
            frame = cam.get_latest_frame()[y1:y2, x1:x2]
            mouse_x, mouse_y = mouse_x - x1, mouse_y - y1
        update_main_img()
        update_info(mouse_x, mouse_y)
        update_hp_calc()
        update_slot_img()
        time.sleep(0.5)
    return

def update_main_img():
    try:
        img = resize_for(frame, (216, 122))
        window["img_main"].update(data=cv2.imencode(".ppm", img)[1].tobytes())
    except: pass
    return

def update_info(x, y):
    global active_hwnd
    active_hwnd = win32gui.GetForegroundWindow()
    window["lbl_mouse_x"].update(value=f"X: {x}")
    window["lbl_mouse_y"].update(value=f"Y: {y}")
    return

def slot_cool_run(idx, sec):
    global slot_cool_ary
    timer_cool_ary[idx] = True
    threading.Timer(sec, timer_cool_down, [idx]).start()

def slot_cool_down(key):
    global slot_cool_ary
    timer_cool_ary[key] = False

def update_slot_img():
    for idx, slot in enumerate(slot_ary):
        if window[f"{slot}_cb_run"].get() == True and slot_img_path_ary[idx] != None:
            x1, y1, x2, y2 = check_four_int(f"{slot}_inp_roi")
            roi_img = frame if isinstance(x1, bool) else frame[y1:y2, x1:x2]
            back_img = resize_for(roi_img, size_roi_img)
            window[f"{slot}_img_roi"].update(data=cv2.imencode(".ppm", back_img)[1].tobytes())
            max_val = 0
            try:
                x, y, w, h, max_val = find_img(roi_img, slot_img_target_ary[idx])
                found_img = roi_img[y:y+h, x:x+w]
                found_img = resize_for(found_img, size_target_image)
                window[f"{slot}_img_res"].update(data=cv2.imencode(".ppm", found_img)[1].tobytes())
                window[f"{slot}_inp_res"].update(value=round(max_val, 2))
            except:
                print("이미지 찾기에 실패했습니다.")

            thres = check_float(f"{slot}_inp_thres")
            key = check_str(f"{slot}_inp_key")
            cool = check_float(f"{slot}_inp_cool")
            if not all([thres, key, cool]):
                print("입력한 변수에 오류가 있습니다.")
            else:
                if max_val > thres and slot_cool_ary[idx] == False:
                    slot_cool_run(idx, cool)
                    send_key(key)

def resize_for_element(element_key, img):
    element_width, element_height = window[element_key].get_size()
    img_height, img_width, img_channel = img.shape
    width_ratio = element_width / img_width
    height_ratio = element_height / img_height
    ratio = min(width_ratio, height_ratio)
    w, h = int(img_width * ratio) , int(img_height * ratio)
    resized_img = cv2.resize(img, dsize=(0,0), fx=ratio, fy=ratio, interpolation=cv2.INTER_LINEAR)
    return resized_img

def resize_for(img, size):
    target_width, target_height = size
    img_height, img_width, img_channel = img.shape
    width_ratio = target_width / img_width
    height_ratio = target_height / img_height
    ratio = min(width_ratio, height_ratio)
    w, h = int(img_width * ratio) , int(img_height * ratio)
    resized_img = cv2.resize(img, dsize=(0,0), fx=ratio, fy=ratio, interpolation=cv2.INTER_LINEAR)
    return resized_img

def apply_to_img_slot():
    global slot_img_path_ary, slot_img_target_ary
    for idx, path in enumerate(slot_img_path_ary):
        if path != None:
            try:
                img = cv2.imread(path)
                slot_img_target_ary[idx] = img
                img = resize_for(img, size_target_image)
                window[f"slot{idx+1}_img_target"].update(data=cv2.imencode(".ppm", img)[1].tobytes())
            except:
                print(f"슬롯{idx+1} 이미지를 불러오는데 실패했습니다.")
                slot_img_path_ary[idx] == None
    return

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

def check_str(key):
    try: return window[key].get()
    except:
        print(f"{key} 변수 변환에 실패했습니다.")
        return False

def check_float(key):
    try: return float(window[key].get())
    except:
        print(f"{key} 변수 변환에 실패했습니다.")
        return False
    
def check_int(key):
    try: return int(window[key].get())
    except:
        print(f"{key} 변수 변환에 실패했습니다.")
        return False
    
def check_two_int(key):
    try:
        input = window[key].get()
        one, two = map(int, input.split(","))
        return one, two
    except:
        print(f"{key} 변수 변환에 실패했습니다.")
        return False, False

def check_four_int(key):
    try:
        input = window[key].get()
        one, two, three, four = map(int, input.split(","))
        return one, two, three, four
    except:
        # print(f"{key} 변수 변환에 실패했습니다.")
        return False, False, False, False

def hp_cool_run(idx, sec):
    global calc_hp_cool_ary
    calc_hp_cool_ary[idx] = True
    threading.Timer(sec, hp_cool_down, [idx]).start()

def hp_cool_down(key):
    global calc_hp_cool_ary
    calc_hp_cool_ary[key] = False

def update_hp_calc():
    for idx, slot in enumerate(calc_hp_ary):
        if window[f"{slot}_cb_run"].get() == True:
            x1, y1, x2, y2 = check_four_int(f"{slot}_inp_roi")
            roi_img = frame if isinstance(x1, bool) else frame[y1:y2, x1:x2]
            img = resize_for(roi_img, (180,20))
            window[f"{slot}_img_input"].update(data=cv2.imencode(".ppm", img)[1].tobytes())
                        
            hp_min, hp_max = check_two_int(f"{slot}_inp_range")
            if hp_min == False and hp_max == False: return

            thres = check_int(f"{slot}_inp_thres")
            if thres == False: return
            
            key = check_str(f"{slot}_inp_key")
            if key == False: return
            
            cool = check_float(f"{slot}_inp_cool")
            if cool == False: return
                                   
            hp_point, res_img = calc_hp(roi_img, thres)
            window[f"{slot}_inp_res"].update(value=hp_point)
            
            res_img = resize_for(res_img, (180,20))
            window[f"{slot}_img_output"].update(data=cv2.imencode(".ppm", res_img)[1].tobytes())

            # 입력제어
            if hp_point >= hp_min and hp_point <= hp_max and calc_hp_cool_ary[idx] == False:
                hp_cool_run(idx, cool)
                print(f"HP분석 슬롯{idx+1} 기능을 사용합니다.")
                send_key(key)

sg.theme("Default1")

size_target_image = (60, 40)
size_roi_img = (130, 70)
size_value_lbl = (10, None)


monitor_screen = sg.Column([
    [sg.Image("", background_color="gray", size=(216, 122), key="img_main")]
])

mouse_info = sg.Column([
    [sg.Text("X: ", expand_x=True, key="lbl_mouse_x")],
    [sg.Text("Y: ", expand_x=True, key="lbl_mouse_y")],
    [sg.Text("P1", size=(2, None)), sg.Input("", key="lbl_p1", justification="center")],
    [sg.Text("P2", size=(2, None)), sg.Input("", key="lbl_p2", justification="center")],
    [sg.Button("영역캡처", expand_x=True, key="btn_capture")],
])

connection = [
    [sg.Text("연결포트"), sg.Combo([""], size=(24, None), key="combo_port", enable_events=True), sg.Button("새로고침", key="btn_refresh_port")],
    [sg.Text(""), sg.Input("여기를 클릭해 입력을 확인하세요.", expand_x=True, key="inp_test", text_color="gray")]
]

timer = [
    [
        sg.Checkbox("실행", key="timer1_cb_run", size=(4, None)),
        sg.Text("입력키", size=(5, None)),
        sg.Input("", key="timer1_inp_key", size=(16, None), justification="center"),
        sg.Text("쿨타임", size=(5, None)),
        sg.Input("", key="timer1_inp_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer2_cb_run", size=(4, None)),
        sg.Text("입력키", size=(5, None)),
        sg.Input("", key="timer2_inp_key", size=(16, None), justification="center"),
        sg.Text("쿨타임", size=(5, None)),
        sg.Input("", key="timer2_inp_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer3_cb_run", size=(4, None)),
        sg.Text("입력키", size=(5, None)),
        sg.Input("", key="timer3_inp_key", size=(16, None), justification="center"),
        sg.Text("쿨타임", size=(5, None)),
        sg.Input("", key="timer3_inp_cool", justification="center"),
    ],
]

hp1_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="hp1_cb_run", size=(3, None)), sg.Text("사용구간"), sg.Input("0,30", size=(6, None), justification="center", key="hp1_inp_range")],
    [sg.Text("관심영역", size=(6, None)), sg.Input("90,32,280,38", key="hp1_inp_roi", expand_x=True, justification="center")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp1_img_input")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp1_img_output")]
])

hp1_lbl = sg.Column([
    [sg.Text("판정값"), sg.Input("210", key="hp1_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("4", key="hp1_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("30", key="hp1_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="hp1_inp_res", expand_x=True, justification="center", readonly=True)],
])

hp2_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="hp2_cb_run", size=(3, None)), sg.Text("사용구간"), sg.Input("0,30", size=(6, None), justification="center", key="hp2_inp_range")],
    [sg.Text("관심영역", size=(6, None)), sg.Input("90,32,280,38", key="hp2_inp_roi", expand_x=True, justification="center")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp2_img_input")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp2_img_output")]
])

hp2_lbl = sg.Column([
    [sg.Text("판정값"), sg.Input("210", key="hp2_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("4", key="hp2_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("30", key="hp2_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="hp2_inp_res", expand_x=True, justification="center", readonly=True)],
])

hp3_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="hp3_cb_run", size=(3, None)), sg.Text("사용구간"), sg.Input("0,30", size=(6, None), justification="center", key="hp3_inp_range")],
    [sg.Text("관심영역", size=(6, None)), sg.Input("90,32,280,38", key="hp3_inp_roi", expand_x=True, justification="center")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp3_img_input")],
    [sg.Image(filename="", background_color="gray", size=(180, 20), key="hp3_img_output")]
])

hp3_lbl = sg.Column([
    [sg.Text("판정값"), sg.Input("210", key="hp3_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("4", key="hp3_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("30", key="hp3_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="hp3_inp_res", expand_x=True, justification="center", readonly=True)],
])

slot1_img = sg.Column([
    [sg.Checkbox("실행", size=(5, None), key="slot1_cb_run"), sg.Button("열기", size=(5, None), key="slot1_btn_open")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot1_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot1_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot1_img_roi")]
])
slot1_lbl = sg.Column([
    [sg.Text("관심영역"), sg.Input("", key="slot1_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot1_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("", key="slot1_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot1_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="slot1_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
])


slot2_img = sg.Column([
    [sg.Checkbox("실행", size=(5, None), key="slot2_cb_run"), sg.Button("열기", size=(5, None), key="slot2_btn_open")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot2_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot2_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot2_img_roi")]
])
slot2_lbl = sg.Column([
    [sg.Text("관심영역"), sg.Input("", key="slot2_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot2_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("", key="slot2_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot2_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="slot2_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
])

slot3_img = sg.Column([
    [sg.Checkbox("실행", size=(5, None), key="slot3_cb_run"), sg.Button("열기", size=(5, None), key="slot3_btn_open")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot3_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot3_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot3_img_roi")]
])
slot3_lbl = sg.Column([
    [sg.Text("관심영역"), sg.Input("", key="slot3_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot3_inp_thres", expand_x=True, justification="center")],
    [sg.Text("입력키"), sg.Input("", key="slot3_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot3_inp_cool", expand_x=True, justification="center")],
    [sg.Text("결과값"), sg.Input("", key="slot3_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
])


layout = [
    [sg.Frame("정보", [
        [sg.Text("캡처대상"), sg.Combo(values=[""], expand_x=True, key="combo_window", enable_events=True), sg.Button("새로고침", key="btn_refresh_hwnd")],
        [sg.Frame("캡처", [[monitor_screen]], size=(240, 160)), sg.Frame("마우스", [[mouse_info]])]
        ])],
    [sg.Frame("아두이노", connection)],
    [sg.Frame("타이머", timer)],
    [sg.Frame("HP분석", [[sg.TabGroup([[sg.Tab("슬롯-1", [[hp1_img, hp1_lbl]]), sg.Tab("슬롯-2", [[hp2_img, hp2_lbl]]), sg.Tab("슬롯-3", [[hp3_img, hp3_lbl]])]])]])],
    # [sg.Frame("HP분석", [[hp1_img, hp1_lbl]])],
    # [sg.Frame("이미지", [[slot1_img, slot1_lbl]])],
    [sg.Frame("이미지", [[sg.TabGroup([[sg.Tab("슬롯-1", [[slot1_img, slot1_lbl]]), sg.Tab("슬롯-2", [[slot2_img, slot2_lbl]]), sg.Tab("슬롯-3", [[slot3_img, slot3_lbl]])]])]])],
    [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]

window = sg.Window(
    app_title,
    layout,
    auto_size_buttons=False,
    auto_size_text=False,
    default_element_size=(8,1),
    finalize=True
    )


# 연결된 포트정보 반영하기
update_port()
ser = False

# 윈도우 창 불러오기
window_ary = []
update_hwnd()
window_select = "전체화면"
window["combo_window"].update(value=window_select)
app_hwnd = [x for x in window_ary if x[0] == app_title][0][1]
active_hwnd = None

# 캡처 설정 및 시작
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=2)
frame = cam.get_latest_frame()

# 프레임 업데이트 쓰레드 시작
threading.Thread(target=update_frame, daemon=True).start()

# 타이머 계산용
timer_ary = ["timer1", "timer2", "timer3"]
timer_cool_ary = []
for timer in timer_ary:
    timer_cool_ary.append(False)
# 타이머 쓰레드 시작
threading.Thread(target=timer_loop, daemon=True).start()

# HP계산용
calc_hp_ary = ["hp1", "hp2", "hp3"]
calc_hp_cool_ary = []
for slot in calc_hp_ary:
    calc_hp_cool_ary.append(False)


# 이미지 계산용
slot_ary = ["slot1", "slot2", "slot3"]
slot_cool_ary = []
slot_img_path_ary = []
slot_img_target_ary = []
for slot in slot_ary:
    slot_cool_ary.append(False)
    slot_img_path_ary.append(None)
    slot_img_target_ary.append(None)


window["inp_test"].bind("<Button-1>", "")
window["inp_test"].bind("<Leave>", "-out")

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break

    elif event == "inp_test":
        window["inp_test"].update(value="", text_color="black")
        send_key("CONNECTED.")

    elif event == "inp_test-out":
        window["inp_test"].update(value="여기를 클릭해 입력을 확인하세요.", text_color="gray")

    elif event == "btn_refresh_port":
        update_port()

    elif event == "combo_port":
        ports_info = window["combo_port"].get()
        connect_port(ports_info)

    elif event == "btn_refresh_hwnd":
        window_select = window["combo_window"].get()
        update_hwnd()
        window["combo_window"].update(value=window_select)

    elif event == "combo_window":
        window_select = window["combo_window"].get()
        if window_select != "전체화면":
            window_select_hwnd = [x[1] for x in window_ary if x[0] == window_select][0]

    elif event == "btn_capture":
        print("영역캡처")
        x1, y1 = check_two_int("lbl_p1")
        x2, y2 = check_two_int("lbl_p2")
        file_name = sg.popup_get_text("저장할 파일명을 입력하세요", title="저장")
        if file_name != None:
            try:
                img_to_save = frame[y1:y2, x1:x2]
                cv2.imwrite(file_name, img_to_save)
                print("파일저장에 성공했습니다.")
            except:
                print("파일저장에 실패했습니다.")

    elif "btn_open" in event:
        slot_name = event.split("_")[0]
        slot_idx = int(slot_name[-1]) - 1
        file_path = sg.popup_get_file("불러올 이미지를 선택하세요.", title="불러오기", file_types=(('Image', '*.png *.jpg *.jpeg'),))
        slot_img_path_ary[slot_idx] = file_path
        apply_to_img_slot()

window.close()