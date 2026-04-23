from flask import Flask, render_template
from flask_socketio import SocketIO
import os
import threading
import time
from typing import Dict, List, Tuple

import base64
import cv2
import numpy as np

import dxcam
import mouse

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")


def cv_to_b64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    return str(im_b64)


def resize_keep_ratio_pad(img, target_w, target_h, pad_color=(0, 0, 0)):
    h, w = img.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas


def main_loop():
    while True:
        frame = cam.get_latest_frame()
        frame = frame[roi[1]:roi[3], roi[0]:roi[2]]
        thumbnail = resize_keep_ratio_pad(frame, preview_width, preview_height)
        
        roi_text = f"ROI:{','.join(map(str, roi))}"
        font = cv2.FONT_HERSHEY_PLAIN
        alpha = 0.5
        size, baseline = cv2.getTextSize(roi_text, font, 1, 1)
        overlay = thumbnail.copy()
        x,y,w,h = 5, 15, size[0], size[1]
        cv2.rectangle(overlay, (x,0), (x+w,y+h-5), (0,0,0), -1)
        cv2.addWeighted(overlay, alpha, thumbnail, 1-alpha, 0, thumbnail)
        cv2.putText(thumbnail, roi_text, (x,y), font, 1, (250,255,255), 1, cv2.LINE_AA)
        thumbnail_b64 = cv_to_b64(thumbnail)
        buffer = {}
        buffer['thumbnail'] = thumbnail_b64
        socketio.emit("stream", buffer)
        time.sleep(0.01)


def run_server():
    socketio.run(app, host="127.0.0.1", port="8000", debug=True, use_reloader=False)


def open_browser():
    os.system('start msedge --app=http://127.0.0.1:8000')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('클라이언트가 연결되었습니다.')
    threading.Thread(target=main_loop, daemon=True).start()
    

@socketio.on('disconnect')
def handle_disconnect():
    print('클라이언트가 연결을 종료했습니다.')
    os._exit(1)


@socketio.on('message')
def handle_message(data:str):
    print('받은 메시지:', data)
    socketio.emit('message', data)


@socketio.on('set_roi_key')
def handle_set_roi_key(p:str):
    global roi
    mx, my = mouse.get_position()
    if p == 'p1':
        if mx < roi[2] and my < roi[3]: 
            roi[0], roi[1] = mx, my
    elif p == 'p2':
        if mx > roi[0] and my > roi[1]:
            roi[2], roi[3] = mx, my
    elif p == 'clear':
        roi = [0,0,screen_width,screen_height]


@socketio.on('set_roi_value')
def handle_set_roi_value(value:List[int]):
    global roi
    if value[0] < value[2] and value[1] < value[3] and value[2] <= screen_width and value[3] <= screen_height:
        roi = value
    else:
        print('Set roi error.')


cam = dxcam.create(output_color='BGR')
cam.start(target_fps=10)

frame = cam.get_latest_frame()
screen_height, screen_width = frame.shape[:2]
roi = [0,0,screen_width,screen_height]

preview_width = 300
preview_height = int(screen_height / (screen_width / preview_width))


threading.Timer(0.1, open_browser).start()
socketio.run(app, host="127.0.0.1", port="8000", debug=True, use_reloader=False)
