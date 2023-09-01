import PySimpleGUI as sg

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
