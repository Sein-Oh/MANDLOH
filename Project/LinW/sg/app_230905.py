import PySimpleGUI as sg
import cv2
import dxcam
import json
import mouse
import numpy as np
import os
import serial
import serial.tools.list_ports as sp
import threading
import time
import win32gui
import win32com.client
# from win32api import GetSystemMetrics

# screen_width = GetSystemMetrics(0)
# screen_height = GetSystemMetrics(1)


default_param = {
    "timer1_key" : "1",
    "timer1_cool" : "3",

    "timer2_key" : "2",
    "timer2_cool" : "3",

    "timer3_key" : "3",
    "timer3_cool" : "3",


    "hp1_roi" : "0,0,220,10",
    "hp1_thres" : "210",
    "hp1_range" : "0,41",
    "hp1_cool" : "30",
    "hp1_key" : "1",

    "hp2_roi" : "0,0,220,10",
    "hp2_thres" : "210",
    "hp2_range" : "0,41",
    "hp2_cool" : "30",
    "hp2_key" : "2",

    "hp3_roi" : "0,0,220,10",
    "hp3_thres" : "210",
    "hp3_range" : "0,41",
    "hp3_cool" : "30",
    "hp3_key" : "3",

    "hp4_roi" : "0,0,220,10",
    "hp4_thres" : "210",
    "hp4_range" : "0,41",
    "hp4_cool" : "30",
    "hp4_key" : "4",

    "hp5_roi" : "0,0,220,10",
    "hp5_thres" : "210",
    "hp5_range" : "0,41",
    "hp5_cool" : "30",
    "hp5_key" : "5",

    "img1_roi" : "전체화면",
    "img1_thres" : "0.8",
    "img1_key" : "1",
    "img1_cool" : "3",
    "img1_path" : "",

    "img2_roi" : "전체화면",
    "img2_thres" : "0.8",
    "img2_key" : "1",
    "img2_cool" : "3",
    "img2_path" : "",


    "img3_roi" : "전체화면",
    "img3_thres" : "0.8",
    "img3_key" : "1",
    "img3_cool" : "3",
    "img3_path" : "",


    "img4_roi" : "전체화면",
    "img4_thres" : "0.8",
    "img4_key" : "1",
    "img4_cool" : "3",
    "img4_path" : "",


    "img5_roi" : "전체화면",
    "img5_thres" : "0.8",
    "img5_key" : "1",
    "img5_cool" : "3",
    "img5_path" : "",
}

func_keys = ["timer1", "timer2", "timer3", "hp1", "hp2", "hp3", "hp4", "hp5", "img1", "img2", "img3", "img4", "img5"]
cooltime = {}
run = {}
for key in func_keys:
    cooltime[key] = False
    run[key] = False

img_dict = { "img1" : "", "img2" : "", "img3" : "", "img4" : "", "img5" : "" }

sg.theme("Default1")
app_title = "IMAGE-SEEKER"

frame_capture = [
    [sg.Text("윈도우", size=(6,None), justification="center"), sg.Combo([""], expand_x=True, key="window_combo", enable_events=True)],
    [sg.Image("", size=(280,160), background_color="gray", key="window_img")]
]

frame_arduino = [
    [sg.Text("연결포트", size=(6,None), justification="center"), sg.Combo([""], expand_x=True, key="arduino_combo", enable_events=True)],
    [sg.Input("여기를 클릭해 입력을 확인하세요.", expand_x=True, text_color="gray", key="arduino_test")]
]

frame_timer = [
    [
        sg.Checkbox("실행", key="timer1_run", enable_events=True ,size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer1_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer1_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer2_run", enable_events=True , size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer2_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer2_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer3_run", enable_events=True , size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer3_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer3_cool", justification="center"),
    ],
]

hp1_tab = [
    [sg.Checkbox("실행", key="hp1_run", enable_events=True), sg.Text("결과값 : 100 (%)", key="hp1_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp1_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp1_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp1_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp1_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp1_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp1_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp1_key")],
]

hp2_tab = [
    [sg.Checkbox("실행", key="hp2_run", enable_events=True), sg.Text("결과값 : 100 (%)", key="hp2_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp2_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp2_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp2_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp2_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp2_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp2_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp2_key")],
]

hp3_tab = [
    [sg.Checkbox("실행", key="hp3_run", enable_events=True), sg.Text("결과값 : 100 (%)", key="hp3_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp3_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp3_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp3_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp3_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp3_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp3_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp3_key")],
]

hp4_tab = [
    [sg.Checkbox("실행", key="hp4_run", enable_events=True), sg.Text("결과값 : 100 (%)", key="hp4_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp4_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp4_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp4_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp4_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp4_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp4_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp4_key")],
]

hp5_tab = [
    [sg.Checkbox("실행", key="hp5_run", enable_events=True), sg.Text("결과값 : 100 (%)", key="hp5_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp5_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp5_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp5_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp5_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp5_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp5_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp5_key")],
]

img1_tab = [
    [sg.Checkbox("실행", key="img1_run", enable_events=True)],
    [sg.Button("파일선택", key="img1_select", expand_x=True), sg.Image("", key="img1_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img1_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img1_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img1_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img1_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img1_cool")],
]

img2_tab = [
    [sg.Checkbox("실행", key="img2_run", enable_events=True)],
    [sg.Button("파일선택", key="img2_select", expand_x=True), sg.Image("", key="img2_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img2_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img2_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img2_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img2_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img2_cool")],
]

img3_tab = [
    [sg.Checkbox("실행", key="img3_run", enable_events=True)],
    [sg.Button("파일선택", key="img3_select", expand_x=True), sg.Image("", key="img3_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img3_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img3_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img3_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img3_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img3_cool")],
]

img4_tab = [
    [sg.Checkbox("실행", key="img4_run", enable_events=True)],
    [sg.Button("파일선택", key="img4_select", expand_x=True), sg.Image("", key="img4_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img4_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img4_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img4_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img4_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img4_cool")],
]

img5_tab = [
    [sg.Checkbox("실행", key="img5_run", enable_events=True)],
    [sg.Button("파일선택", key="img5_select", expand_x=True), sg.Image("", key="img5_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img5_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img5_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img5_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img5_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img5_cool")],
]


layout = [
    [sg.Frame("캡처 (➖)", frame_capture, key="frame_capture", size=(300,220), metadata=True, element_justification="center")],
    [sg.Frame("아두이노 (➖)", frame_arduino, key="frame_arduino", size=(300,70), metadata=True)],
    [sg.Frame("타이머 (➖)", frame_timer, key="frame_timer" ,size=(300,25), metadata=False)],
    [sg.Frame("HP분석 (➖)", [[sg.TabGroup([[sg.Tab("슬롯-1", hp1_tab), sg.Tab("슬롯-2", hp2_tab), sg.Tab("슬롯-3", hp3_tab), sg.Tab("슬롯-4", hp4_tab), sg.Tab("슬롯-5", hp5_tab)]])]], size=(300,25), key="frame_hp", metadata=False)],
    [sg.Frame("Img찾기 (➖)", [[sg.TabGroup([[sg.Tab("슬롯-1", img1_tab), sg.Tab("슬롯-2", img2_tab), sg.Tab("슬롯-3", img3_tab), sg.Tab("슬롯-4", img4_tab), sg.Tab("슬롯-5", img5_tab)]])]], size=(300,25), key="frame_img", metadata=False)],
    [sg.Button("crop")]
]

window = sg.Window(app_title, layout, finalize=True)
window["frame_capture"].bind("<Button-1>", "")
window["frame_arduino"].bind("<Button-1>", "")
window["frame_timer"].bind("<Button-1>", "")
window["frame_hp"].bind("<Button-1>", "")
window["frame_img"].bind("<Button-1>", "")
window["arduino_test"].bind("<Button-1>", "")
window["arduino_test"].bind("<Leave>", "-out")

for key in default_param.keys():
    if "path" not in key:
        window[key].bind("<Return>", "-submit")



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
    window["window_combo"].update(values=win_title_ary)
    return


def find_port():
    res = []
    for port, desc, hwid in sorted(sp.comports()):
        res.append(f"{port}, {desc}")
    return res


def update_port():
    list = find_port()
    window["arduino_combo"].update(values=list, value=list[0])
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
    return


def send_key(keys, announce=False, win_ignore=True):
    if announce == True:
        print(f"입력키 : {keys}")

    # if active_hwnd == app_hwnd and win_ignore == True:
    #     print("앱을 선택하고 있어 입력을 무시합니다.")
    #     return

    if ser == False:
        print("아두이노가 연결되지 않았습니다.")
        return
    
    key_ary = keys.split(",")
    for key in key_ary:
        if "-" in key:
            t = float(key[1:])
            print(t)
            time.sleep(t)
        else:
            ser.write(key.encode())
    return


def crop_image():
    full_screen = cam.get_latest_frame()
    cv2.namedWindow('ROI',cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('ROI', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    x,y,w,h = cv2.selectROI("ROI", full_screen)
    img = full_screen[y:y+h, x:x+w]
    cv2.imwrite("capture.jpg", img)
    cv2.destroyWindow("ROI")
    return


def resize_for(img, size):
    target_width, target_height = size
    img_height, img_width, img_channel = img.shape
    if img_width > target_width or img_height > target_height:
        width_ratio = target_width / img_width
        height_ratio = target_height / img_height
        ratio = min(width_ratio, height_ratio)
        w, h = int(img_width * ratio) , int(img_height * ratio)
        img = cv2.resize(img, dsize=(0,0), fx=ratio, fy=ratio, interpolation=cv2.INTER_LINEAR)
        img_height, img_width, img_channel = img.shape
    # calculate padding
    dmod_w = divmod((target_width-img_width), 2)
    dmod_h = divmod((target_height-img_height), 2)
    l, r = dmod_w[0], sum(dmod_w)
    t, b = dmod_h[0], sum(dmod_h)
    return cv2.copyMakeBorder(img, t, b, l, r, cv2.BORDER_CONSTANT, 0)


def update_capture_preview(frame, x, y):
    try:
        preview = resize_for(frame, (280,160))
        cv2.putText(preview, f"X:{x}", (5, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50,250,50), 1)
        cv2.putText(preview, f"Y:{y}", (5, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50,250,50), 1)
        window["window_img"].update(data=cv2.imencode(".ppm", preview)[1].tobytes())
    except: pass
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

def update_hp(frame):
    try:
        for key in run.keys():
            if "hp" in key and run[key] == True:
                hp_min, hp_max = map(int, window[f"{key}_range"].get().split(","))
                x1, y1, x2, y2 = map(int, window[f"{key}_roi"].get().split(","))
                roi_img = frame[y1:y2, x1:x2]
                point, thres_img = calc_hp(roi_img, 210)
                window[f"{key}_result"].update(f"결과값 : {point} (%)")
                resized_img = resize_for(roi_img, (200,10))
                resized_thres_img = resize_for(thres_img, (200,10))
                window[f"{key}_input_img"].update(data=cv2.imencode(".ppm", resized_img)[1].tobytes())
                window[f"{key}_output_img"].update(data=cv2.imencode(".ppm", resized_thres_img)[1].tobytes())
    except: pass
    return


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
        update_capture_preview(frame, mouse_x, mouse_y)
        update_hp(frame)
        time.sleep(0.5)
    return


def update_param(param):
    for key in param.keys():
        if "path" not in key:
            window[key].update(value=param[key])
    update_img_slot()


def load_data(path):
    with open(path, "r") as file:
        return json.load(file)


def select_image(event):
    global param
    slot = event.split("_")[0]
    file_path = sg.popup_get_file("불러올 이미지를 선택하세요.", title="불러오기", file_types=(('Image', '*.png *.jpg *.jpeg'),))
    if file_path == None or file_path == "":
        print("이미지를 선택하세요.")
        return
    param[f"{slot}_path"] = file_path
    update_img_slot()
    return

def update_img_slot():
    for key in param.keys():
        if "path" in key and param[key] != "":
            slot = key.split("_")[0]
            try:
                img = cv2.imread(param[key])
                resized_img = resize_for(img, (200,25))
                window[f"{slot}_img"].update(data=cv2.imencode(".ppm", resized_img)[1].tobytes())
            except: pass


# 사용중인 설정파일 확인 및 적용
param = load_data("userdata.json") if os.path.isfile("userdata.json") else default_param
update_param(param)


# 연결된 포트정보 반영하기
# update_port()
ser = False


# 윈도우 창 불러오기
window_ary = []
update_hwnd()
window_select = "전체화면"
window["window_combo"].update(value=window_select)
app_hwnd = [x for x in window_ary if x[0] == app_title][0][1]
active_hwnd = None


# 캡처 설정 및 시작
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=2)
frame = cam.get_latest_frame()


# 프레임 업데이트 쓰레드 시작
threading.Thread(target=update_frame, daemon=True).start()


while True:
    event, values = window.read()


    if event == sg.WINDOW_CLOSED or event == "종료하기":
        break


    elif event == "frame_capture":
        window["frame_capture"].metadata = check = not window["frame_capture"].metadata
        window["frame_capture"].update(value="캡처 (➖)" if check == True else "캡처 (➕)")
        window["frame_capture"].set_size(size=(300,220) if check == True else (300,25))


    elif event == "frame_arduino":
        window["frame_arduino"].metadata = check = not window["frame_arduino"].metadata
        window["frame_arduino"].update(value="아두이노 (➖)" if check == True else "아두이노 (➕)")
        window["frame_arduino"].set_size(size=(300,70) if check == True else (300,25))


    elif event == "frame_timer":
        window["frame_timer"].metadata = check = not window["frame_timer"].metadata
        window["frame_timer"].update(value="타이머 (➖)" if check == True else "타이머 (➕)")
        window["frame_timer"].set_size(size=(300,110) if check == True else (300,25))
        

    elif event == "frame_hp":
        window["frame_hp"].metadata = check = not window["frame_hp"].metadata
        window["frame_hp"].update(value="HP분석 (➖)" if check == True else "HP분석 (➕)")
        window["frame_hp"].set_size(size=(300,220) if check == True else (300,25))
        

    elif event == "frame_img":
        window["frame_img"].metadata = check = not window["frame_img"].metadata
        window["frame_img"].update(value="Img찾기 (➖)" if check == True else "Img찾기 (➕)")
        window["frame_img"].set_size(size=(300,300) if check == True else (300,25))


    elif event == "window_combo":
        window_select = window["window_combo"].get()
        if window_select != "전체화면":
            window_select_hwnd = [x[1] for x in window_ary if x[0] == window_select][0]


    elif event == "arduino_combo":
        ports_info = window["arduino_combo"].get()
        connect_port(ports_info)


    elif event == "arduino_test":
        window["arduino_test"].update(value="", text_color="black")
        send_key("CONNECTED.", win_ignore=False)


    elif event == "arduino_test-out":
        window["arduino_test"].update(value="여기를 클릭해 입력을 확인하세요.", text_color="gray")


    elif "select" in event:
        select_image(event)


    elif "run" in event:
        slot = event.split("_")[0]
        run[slot] = window[event].get()


    elif "-submit" in event:
        slot = event.split("-")[0]
        value = window[slot].get()
        print(f"{slot} 값이 {param[slot]}에서 {value}으로 변경되었습니다.")
        param[slot] = value


    elif event == "crop":
        threading.Thread(target=crop_image, daemon=True).start()
        print("crop")


window.close()
