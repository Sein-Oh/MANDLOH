from aiohttp import web
import socketio
import os
import time
import signal
import win32gui, win32com.client
import threading
import PySimpleGUI as sg

# 정적 호스팅 서버를 이용하기 위한 cors 옵션 추가.
# 별도 클라이언트를 띄워주지 않는다.
sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

shell = win32com.client.Dispatch("WScript.Shell")

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

@sio.event
def setForeground(sid, hwnd):
    shell.SendKeys('%')    
    win32gui.SetForegroundWindow(hwnd)
    return True

def runSocketServer():
    web.run_app(app, host="localhost", port=8080)

def run():
    t = threading.Thread(target=runSocketServer)
    t.daemon = True
    t.start()

run()
while True:
    print("SLEEP")
    time.sleep(3)
