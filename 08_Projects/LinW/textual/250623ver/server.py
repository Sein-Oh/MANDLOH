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

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30


# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)


#플라스크 웹서버 생성
app = Flask(__name__)
CORS(app)

#화면캡처 생성
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=fps)
print(f"캡처 시작: {fps} FPS")


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
# t_prev = time.time()
def gen():
    global t_prev
    while True:
        # t = time.time()
        # print(t - t_prev)
        # t_prev = t
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
    print(cmd)
    ser.write(cmd.encode())
    return Response(status=204)

app.run(host="localhost", port=port, debug=False, threaded=True, use_reloader=False)