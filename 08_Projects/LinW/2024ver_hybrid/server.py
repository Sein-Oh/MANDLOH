#!/usr/bin/env python
from flask import Flask, Response
from flask_cors import CORS, cross_origin
import io
import cv2
import dxcam
from datetime import datetime
import serial
import serial.tools.list_ports as sp
import logging
import os
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#아두이노 포트 확인
def find_port():
    res = []
    for port, desc, hwid in sorted(sp.comports()):
        res.append(f"{port}, {desc}")
    return res

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
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

#라우팅 구성
@app.route("/")
@cross_origin()
def video_feed():
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/check")
@cross_origin()
def server_check():
    print("서버연결 확인")
    return "OK"


@app.route("/input/<cmd>")
@cross_origin()
def control(cmd):
    clock = datetime.now().time()
    print(f"[{clock:%T}] {cmd}")
    ser.write(cmd.encode())
    return Response(status=204)


#아두이노 포트 선택
ports = find_port()
for idx, port in enumerate(ports):
    print(f"{idx}) - {port}")
while True:
    user_input = input("연결할 보드의 숫자를 입력하세요: ")
    try:
        select = int(user_input)
        if select < 0 or select >= len(ports):
            print("에러. 올바른 숫자를 입력하세요.")
        else: break
    except:
        print("에러. 올바른 숫자를 입력하세요.")
arduino_port = ports[select].split(",")[0]
try:
    ser = serial.Serial(port=arduino_port, baudrate=9600)
    print(f"{arduino_port}에 연결되었습니다.")
except:
    print(f"{arduino_port}연결에 실패했습니다. 앱을 종료합니다.")
    os._exit(1)

print(f"http://127.0.0.1:8000")
print("종료는 Ctrl + c 를 입력하세요.")
app.run(host="127.0.0.1", port=8000, debug=False, threaded=True, use_reloader=False)
