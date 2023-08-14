
import PySimpleGUI as sg
import cv2
import dxcam
import mouse
import numpy as np
import serial
import serial.tools.list_ports as sp
import threading
import time


def find_port():
    res = []
    for port, desc, hwid in sorted(sp.comports()):
        res.append(f"{port}, {desc}")
    return res

def update_port():
    list = find_port()
    window["combo_port"].update(values=list, value=list[0])
    return

def update_frame():
    global frame
    while True:
        frame = cam.get_latest_frame()
        update_main_img()
        update_info()
        time.sleep(0.5)
    return

def update_main_img():
    img = resize_for_element("img_main", frame)
    window["img_main"].update(data=cv2.imencode(".ppm", img)[1].tobytes())
    return

def update_info():
    mouse_x, mouse_y = mouse.get_position()
    window["lbl_mouse_x"].update(value=f"X: {mouse_x}")
    window["lbl_mouse_y"].update(value=f"Y: {mouse_y}")
    return

def resize_for_element(element_key, img):
    element_width, element_height = window[element_key].get_size()
    img_height, img_width, img_channel = img.shape
    width_ratio = element_width / img_width
    height_ratio = element_height / img_height
    ratio = min(width_ratio, height_ratio)
    w, h = int(img_width * ratio) , int(img_height * ratio)
    resized_img = cv2.resize(img, dsize=(0,0), fx=ratio, fy=ratio, interpolation=cv2.INTER_LINEAR)
    return resized_img

sg.theme("Default1")

size_target_image = (60, 40)
size_roi_img = (130, 70)
size_value_lbl = (10, None)


mouse_info = sg.Column([
    [sg.Text("X: ", expand_x=True, key="lbl_mouse_x")],
    [sg.Text("Y: ", expand_x=True, key="lbl_mouse_y")],
    [sg.Text("P1", size=(2, None)), sg.Input("", key="lbl_p1", justification="center")],
    [sg.Text("P2", size=(2, None)), sg.Input("", key="lbl_p2", justification="center")],
    [sg.Button("영역캡처", expand_x=True, key="btn_capture")],
])


monitor_screen = sg.Column([
    [sg.Image("", background_color="gray", size=(216, 122), key="img_main")]
])


connection = [
    [sg.Text("연결포트"), sg.Combo([""], size=(24, None), key="combo_port"), sg.Button("새로고침", key="btn_refresh")],
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
        sg.Checkbox("실행", key="timer2_cb_run", size=(4, None)),
        sg.Text("입력키", size=(5, None)),
        sg.Input("", key="timer2_inp_key", size=(16, None), justification="center"),
        sg.Text("쿨타임", size=(5, None)),
        sg.Input("", key="timer2_inp_cool", justification="center"),
    ],
]

slot1_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="slot1_cb_run")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot1_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot1_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot1_img_roi")]
])
slot1_lbl = sg.Column([
    [sg.Text("결과값"), sg.Input("", key="slot1_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
    [sg.Text("입력키"), sg.Input("", key="slot1_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot1_inp_cool", expand_x=True, justification="center")],
    [sg.Text("관심영역"), sg.Input("", key="slot1_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot1_inp_thres", expand_x=True, justification="center")],
])


slot2_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="slot2_cb_run")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot2_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot2_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot2_img_roi")]
])
slot2_lbl = sg.Column([
    [sg.Text("결과값"), sg.Input("", key="slot2_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
    [sg.Text("입력키"), sg.Input("", key="slot2_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot2_inp_cool", expand_x=True, justification="center")],
    [sg.Text("관심영역"), sg.Input("", key="slot2_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot2_inp_thres", expand_x=True, justification="center")],
])

slot3_img = sg.Column([
    [sg.Checkbox("실행", expand_x=True, key="slot3_cb_run")],
    [
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot3_img_target"),
        sg.Image(filename="", background_color="gray", size=size_target_image, key="slot3_img_res")
    ],
    [sg.Image(filename="", background_color="gray", size=size_roi_img, key="slot3_img_roi")]
])
slot3_lbl = sg.Column([
    [sg.Text("결과값"), sg.Input("", key="slot3_inp_res", expand_x=True, justification="center", size=(16,None), readonly=True)],
    [sg.Text("입력키"), sg.Input("", key="slot3_inp_key", expand_x=True, justification="center")],
    [sg.Text("쿨타임"), sg.Input("", key="slot3_inp_cool", expand_x=True, justification="center")],
    [sg.Text("관심영역"), sg.Input("", key="slot3_inp_roi", expand_x=True, justification="center")],
    [sg.Text("판정값"), sg.Input("", key="slot3_inp_thres", expand_x=True, justification="center")],
])


layout = [
    [sg.Frame("정보", [[sg.Frame("캡처", [[monitor_screen]]), sg.Frame("마우스", [[mouse_info]])]])],
    [sg.Frame("아두이노", connection)],
    [sg.Frame("타이머", timer)],
    [sg.Frame("이미지", [[sg.TabGroup([[sg.Tab("슬롯-1", [[slot1_img, slot1_lbl]]), sg.Tab("슬롯-2", [[slot2_img, slot2_lbl]]), sg.Tab("슬롯-3", [[slot3_img, slot3_lbl]])]])]])],
    # [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True, justification="center")]
]

window = sg.Window(
    "GUI",
    layout,
    auto_size_buttons=False,
    auto_size_text=False,
    default_element_size=(8,1),
    finalize=True
    )


# 연결된 포트정보 반영하기
update_port()

# 캡처 설정 및 시작
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=2)
frame = cam.get_latest_frame()

# 프레임 업데이트 쓰레드 시작
threading.Thread(target=update_frame, daemon=True).start()

window["inp_test"].bind("<Button-1>", "")
window["inp_test"].bind("<Leave>", "-out")



while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break

    elif event == "inp_test":
        window["inp_test"].update(value="", text_color="black")

    elif event == "inp_test-out":
        window["inp_test"].update(value="여기를 클릭해 입력을 확인하세요.", text_color="gray")


    elif event == "btn_refresh":
        update_port()



window.close()
