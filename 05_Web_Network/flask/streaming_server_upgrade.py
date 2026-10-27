#!/usr/bin/env python
from flask import Flask, Response
from flask_cors import CORS
import io
import cv2
import dxcam
import win32gui
import os
import keyboard
import logging
import time
import threading

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

#플라스크 웹서버 생성
app = Flask(__name__)
CORS(app)

#화면캡처 생성
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=30)
frame_ori = cam.get_latest_frame()

def capture():
    global frame_ori
    while True:
        frame_ori = cam.get_latest_frame()

threading.Thread(target=capture, daemon=True).start()

t_prev = 0
#스트리밍 구현부
def gen():
    global t_prev
    while True:
        time.sleep(0.1)
        t = time.time()
        print(t - t_prev)
        t_prev = t
        # frame = cam.get_latest_frame()
        frame = frame_ori.copy()
        if win_hwnd != 0:
            x1, y1, x2, y2 = get_win_size(win_hwnd)
            frame = frame[y1:y2, x1:x2]
        # frame = cv2.resize(frame, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

def gen_crop(x1,y1,x2,y2):
    while True:
        # frame = cam.get_latest_frame()
        frame = frame_ori.copy()
        frame = frame[y1:y2, x1:x2]
        # frame = cv2.resize(frame, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
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

@app.route("/crop/<x1>/<y1>/<x2>/<y2>")
def crop_feed(x1, y1, x2, y2):
    return Response(
        gen_crop(int(x1), int(y1), int(x2), int(y2)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/input/<cmd>")
def say(cmd):
    print(cmd)
    keyboard.write(cmd)
    return Response(status=204)


#윈도우 목록 받기
win_list = get_win_list()
win_list.insert(0, ('전체화면', 0))
for i in range(len(win_list)):
    print(f'{i} - {win_list[i][0]}')

#command line으로 입력받는 부분
while True:    
    user_input = input("캡처할 윈도우의 숫자를 입력하세요 : ")
    try:
        select = int(user_input)
        #잘못된 숫자입력 처리
        if select < 0 or select >= len(win_list):
            print("에러. 올바른 숫자를 입력하세요.")
        else: break
    except:
        print("에러. 올바른 숫자를 입력하세요.")

win_hwnd = win_list[select][1]
print(f'{win_list[select][0]}의 스트리밍을 시작합니다.')
print(f"http://127.0.0.1:8000")
print("종료는 Ctrl + c 를 입력하세요.")
app.run(host="127.0.0.1", port=8000, debug=False, threaded=True, use_reloader=False)
