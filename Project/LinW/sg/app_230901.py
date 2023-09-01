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

sg.theme("Default1")
app_title = "MANDLOH-IMG"

frame_capture = [
    [sg.Text("윈도우", size=(6,None), justification="center"), sg.Combo([""], expand_x=True, key="window_combo")],
    [sg.Image("", size=(280,160), background_color="gray", key="window_img")]
]

frame_arduino = [
    [sg.Text("연결포트", size=(6,None), justification="center"), sg.Combo([""], expand_x=True, key="arduino_combo")],
    [sg.Input("클릭하여 입력상태를 확인합니다.", expand_x=True, text_color="gray", key="arduino_test")]
]

frame_timer = [
    [
        sg.Checkbox("실행", key="timer1_run", size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer1_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer1_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer2run", size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer2_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer2_cool", justification="center"),
    ],
    [
        sg.Checkbox("실행", key="timer3_run", size=(3,None)),
        sg.Text("입력키", size=(5,None)),
        sg.Input("", key="timer3_key", size=(10,None), justification="center"),
        sg.Text("쿨타임", size=(5,None)),
        sg.Input("", key="timer3_cool", justification="center"),
    ],
]

hp1_tab = [
    [sg.Checkbox("실행", key="hp1_run"), sg.Text("결과값 : 100 (%)", key="hp1_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp1_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp1_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp1_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp1_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp1_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp1_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp1_key")],
]

hp2_tab = [
    [sg.Checkbox("실행", key="hp2_run"), sg.Text("결과값 : 100 (%)", key="hp2_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp2_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp2_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp2_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp2_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp2_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp2_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp2_key")],
]

hp3_tab = [
    [sg.Checkbox("실행", key="hp3_run"), sg.Text("결과값 : 100 (%)", key="hp3_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp3_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp3_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp3_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp3_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp3_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp3_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp3_key")],
]

hp4_tab = [
    [sg.Checkbox("실행", key="hp4_run"), sg.Text("결과값 : 100 (%)", key="hp4_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp4_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp4_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp4_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp4_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp4_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp4_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp4_key")],
]

hp5_tab = [
    [sg.Checkbox("실행", key="hp5_run"), sg.Text("결과값 : 100 (%)", key="hp5_result")],
    [sg.Text("인식", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp5_input_img")],
    [sg.Text("분석", size=(6,None)), sg.Image("", background_color="gray", size=(200,10), key="hp5_output_img")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp5_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="hp5_thres")],
    [sg.Text("사용구간", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="hp5_range"), sg.Text("쿨타임"), sg.Input("", justification="center", key="hp5_cool")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", expand_x=True, justification="center", key="hp5_key")],
]

img1_tab = [
    [sg.Button("파일선택", key="img1_select", expand_x=True), sg.Image("", key="img1_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img1_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img1_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img1_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img1_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img1_cool")],
]

img2_tab = [
    [sg.Button("파일선택", key="img2_select", expand_x=True), sg.Image("", key="img2_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img2_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img2_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img2_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img2_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img2_cool")],
]

img3_tab = [
    [sg.Button("파일선택", key="img3_select", expand_x=True), sg.Image("", key="img3_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img3_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img3_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img3_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img3_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img3_cool")],
]

img4_tab = [
    [sg.Button("파일선택", key="img4_select", expand_x=True), sg.Image("", key="img4_img" ,background_color="gray", size=(200,25))],
    [sg.Image("", size=(280,120), background_color="gray", key="img4_preview")],
    [sg.Text("관심영역", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img4_roi"), sg.Text("판정값"), sg.Input("", justification="center", key="img4_thres")],
    [sg.Text("입력키", size=(6,None)), sg.Input("", size=(14,None), justification="center", key="img4_key"), sg.Text("쿨타임"), sg.Input("", justification="center", key="img4_cool")],
]

img5_tab = [
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
    [sg.Frame("Img찾기 (➖)", [[sg.TabGroup([[sg.Tab("슬롯-1", img1_tab), sg.Tab("슬롯-2", img2_tab), sg.Tab("슬롯-3", img3_tab), sg.Tab("슬롯-4", img4_tab), sg.Tab("슬롯-5", img5_tab)]])]], size=(300,25), key="frame_img", metadata=False)]    
]

window = sg.Window(app_title, layout, finalize=True)
window["frame_capture"].bind("<Button-1>", "")
window["frame_arduino"].bind("<Button-1>", "")
window["frame_timer"].bind("<Button-1>", "")
window["frame_hp"].bind("<Button-1>", "")
window["frame_img"].bind("<Button-1>", "")


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


def update_capture_preview(frame):
    preview = resize_for(frame, (280,160))
    window["window_img"].update(data=cv2.imencode(".ppm", preview)[1].tobytes())

def update_frame():
    global frame
    while True:
        frame = cam.get_latest_frame()
        update_capture_preview(frame)
        time.sleep(0.5)


# 연결된 포트정보 반영하기
update_port()
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
        window["frame_capture"].set_size(size=(300,170) if check == True else (300,25))


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
        window["frame_hp"].set_size(size=(300,210) if check == True else (300,25))
        
    elif event == "frame_img":
        window["frame_img"].metadata = check = not window["frame_img"].metadata
        window["frame_img"].update(value="Img찾기 (➖)" if check == True else "Img찾기 (➕)")
        window["frame_img"].set_size(size=(300,260) if check == True else (300,25))


window.close()
