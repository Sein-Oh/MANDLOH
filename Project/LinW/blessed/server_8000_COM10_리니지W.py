#!/usr/bin/env python
from flask import Flask, Response
from flask_cors import CORS
from datetime import datetime
import io
import cv2
import dxcam
import win32gui
import logging
import os
import serial

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

win_hwnd = 0

#윈도우에 실행중인 프로그램 목록 가져오기
def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

#특정 윈도우가 있는 위치 및 크기 가져오기
def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

def find_window(target):
    win_ary = get_win_list()
    for win in win_ary:
        if target in win[0]:
            target_text = win[0]
            target_hwnd = win[1]
    return target_hwnd, target_text

#플라스크 웹서버 생성
app = Flask(__name__)
CORS(app)

#화면캡처 생성
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=30)

#스트리밍 구현부
def gen():
    while True:
        frame = cam.get_latest_frame()
        if win_hwnd != 0:
            x1, y1, x2, y2 = get_win_size(win_hwnd)
            frame = frame[y1:y2, x1:x2]
        # frame = cv2.resize(frame, dsize=(1280,720), interpolation=cv2.INTER_AREA)
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

#라우팅 구성
@app.route('/')
def video_feed():
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/check")
def check():
    return "OK"


@app.route('/input/<cmd>')
def get_input(cmd):
    clock = datetime.now().time()
    ser.write(cmd.encode())
    msg = f"[{clock:%T}] {cmd}"
    # print(msg)
    return Response(status=204)

#파일명으로부터 변수 받기. 파일명은 server_PORT_COM_TARGET.py
file_name = os.path.abspath(__file__).split("\\")[-1]
port = int(file_name.split("_")[1])
com = file_name.split("_")[2]
target_name = file_name.split("_")[3].split(".")[0]

win_hwnd, win_text = find_window(target_name)
ser = serial.Serial(port=com, baudrate=9600)

print(f"URL: http://127.0.0.1:{port}")
print(f"캡처 대상: {win_text}")
print(f"아두이노 포트 : {com}")
print("종료는 Ctrl + c 를 입력하세요.")
app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)