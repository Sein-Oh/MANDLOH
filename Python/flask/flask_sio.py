from flask import Flask, render_template
from flask_socketio import SocketIO
import os
import threading
import time

import base64
import cv2
import numpy as np
import json
import requests

import dxcam


app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")


def cv_to_b64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    return str(im_b64)


def main_loop():
    while True:
        frame = cam.get_latest_frame()
        thumbnail = cv2.resize(frame, dsize=(0,0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        thumbnail_b64 = cv_to_b64(thumbnail)
        socketio.emit("stream", thumbnail_b64)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit("time_event", now)
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
def handle_message(data):
    print('받은 메시지:', data)
    socketio.emit('message', data)


cam = dxcam.create(output_color="BGR")
cam.start(target_fps=10)
frame = cam.get_latest_frame()


threading.Timer(0.1, open_browser).start()
socketio.run(app, host="127.0.0.1", port="8000", debug=True, use_reloader=False)
