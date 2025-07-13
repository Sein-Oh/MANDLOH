from aiohttp import web
import socketio
import os
import time
import signal
import threading

import dxcam
import base64
import cv2
import numpy as np
import json


# 정적 호스팅 서버를 이용하기 위한 cors 옵션 추가.
# 별도 클라이언트를 띄워주지 않는다.
sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

def b64_to_cv(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(",")[1]), np.uint8), cv2.IMREAD_COLOR)


def cv_to_b64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    # js => img.src = `data:image/png;base64,${data.slice(2, -1)}`
    return str(im_b64)


def cv_to_b64t(img):
    ret, buffer = cv2.imencode(".jpg", img)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    # js => img.src = "data:image/jpeg;base64," + data;
    return jpg_as_text


def ctrlC(signum, frame):
    print("앱을 종료합니다.")
    os._exit(1) #강제종료

signal.signal(signal.SIGINT, ctrlC)

@sio.event
def connect(sid, environ):
    print(f"클라이언트[{sid}]가 연결되었습니다.")

@sio.event
def disconnect(sid):
    print(f"클라이언트[{sid}]의 연결이 종료되었습니다.")
    os._exit(1)  # 강제종료

@sio.event
def message(sid, data):
    print(f"클라이언트[{sid}]로부터 메시지를 받았습니다: {data}")
    # sio.send(sid, f"서버로부터의 응답: {data}")
    return f"서버로부터의 응답: {data}"


@sio.event
def get_thumbnail(sid):
    thumbnail = cv2.resize(frame, dsize=(0,0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    # thumbnail_b64 = cv_to_b64t(thumbnail)
    thumbnail_b64 = cv_to_b64(thumbnail)
    return thumbnail_b64

def open_browser():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'index.html')
    os.system(f'start msedge --app="{html_path}"')


def runSocketServer():
    web.run_app(app, host="localhost", port=8080)

threading.Thread(target=runSocketServer, daemon=True).start()
open_browser()

cam = dxcam.create(output_color="BGR")
cam.start(target_fps=10)


while True:
    frame = cam.get_latest_frame()
    print("SLEEP")
    
