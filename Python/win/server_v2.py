#!/usr/bin/env python
from flask import Flask, Response
from flask_cors import CORS
import io
import cv2
import dxcam
import serial
import serial.tools.list_ports
import sys
import time
import os
import mouse
import blessed
import threading
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
term = blessed.Terminal()

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 5


#플라스크 웹서버 생성
app = Flask(__name__)
CORS(app)

#화면캡처 생성
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=fps)
frame = cam.get_latest_frame()
height, width, _ = frame.shape
#print(f"캡처 시작: {fps} FPS {width}x{height}")



#포트 설정
def find_ports():
    ports = serial.tools.list_ports.comports()
    port_list = []
    for port in ports:
        port_list.append(port.device)
    return port_list

def connect_serial():
    ports = find_ports()
    if len(ports) < 1:
        print("연결 가능한 시리얼 포트가 없습니다.")
        return None
    else:
        for port in ports:
            try:
                ser = serial.Serial(port, baudrate=9600, timeout=1)
                ser.write(b"check")
                if ser.readline() == b"OK\r\n":
                    print(f"시리얼 포트 {port} 연결 성공")
                    return ser
            except:
                print("연결에 실패했습니다.")
                return None
ser = connect_serial()

#스트리밍 구현부
def gen():
    while True:
        frame = cam.get_latest_frame()
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

#라우팅 구성
@app.route('/')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/input/<cmd>')
def get_input(cmd):
    if "," in cmd:
        x, y = list(map(int, cmd.split(",")))
        mx = int(x / width * 1000)
        my = int(y / height * 1000)
        cmd = f"{mx},{my}"
    ser.write(cmd.encode())
    return Response(status=204)


def terminal():
    with term.cbreak(), term.hidden_cursor():
        os.system('cls' if os.name == 'nt' else 'clear')
        while True:
            with term.location(0, 0):
                print(term.black_on_white("=== Streaming Server ".ljust(40, "=")))
                print(f" Address : http://localhost:{port}")
                print(f" Size    : {width}x{height}")
                print(f" FPS     : {fps}")

            with term.location(0, 5):
                print(term.black_on_white("=== Input Server ".ljust(40, "=")))
                print(f" Address : http://localhost:{port}/input")
                print(f" Serial  : {ser.name if ser else 'Not connected'}")
            
            with term.location(0, 9):
                x, y = mouse.get_position()
                print(term.black_on_white("=== Mouse Position ".ljust(40, "=")))
                print(f" X : {x}".ljust(term.width))
                print(f" Y : {y}".ljust(term.width))

            time.sleep(0.2)
      



threading.Thread(target=terminal, daemon=True).start()
app.run(host="localhost", port=port, debug=False, threaded=True, use_reloader=False)