from aiohttp import web
import socketio
import os
import time
import signal
import threading

# 정적 호스팅 서버를 이용하기 위한 cors 옵션 추가.
# 별도 클라이언트를 띄워주지 않는다.
sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

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


def open_browser():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'index.html')
    os.system(f'start msedge --app="{html_path}"')


def runSocketServer():
    web.run_app(app, host="localhost", port=8080)

threading.Thread(target=runSocketServer, daemon=True).start()
open_browser()

while True:
    print("SLEEP")
    time.sleep(3)
