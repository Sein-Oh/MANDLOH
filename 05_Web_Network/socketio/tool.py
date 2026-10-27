from aiohttp import web
import base64
import cv2
import mouse
import numpy as np
import os
import socketio
import signal
import time
import win32gui, win32ui, win32con, win32api, win32com.client

# 정적 호스팅 서버를 이용하기 위한 cors 옵션 추가.
# 별도 클라이언트를 띄워주지 않는다.
sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

def signalHandler(signal, frame):
    print("강제종료")
    os._exit(1)

def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)

@sio.event
def getWinList(sid):
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

@sio.event
def getInnerWindows(sid, whndl):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            hwnds[win32gui.GetClassName(hwnd)] = hwnd
        return True
    hwnds = {}
    win32gui.EnumChildWindows(whndl, callback, hwnds)
    return hwnds


controlHwnd = False
controlWin = False
def makeControlWin(hwnd):
    global controlHwnd, controlWin
    if hwnd != controlHwnd:
        controlHwnd = hwnd
        controlWin = win32ui.CreateWindowFromHandle(hwnd)
    return controlWin

@sio.event
def controlClick(sid, hwnd, x, y, delay=0.1):
    try:
        win = makeControlWin(hwnd)
        lParam = win32api.MAKELONG(x, y)
        win.PostMessage(win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(delay)
        win.PostMessage(win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam)
        return True
    except:
        return False

@sio.event
def controlKey(sid, hwnd, key, delay=0.1):
    try:
        win = makeControlWin(hwnd)
        win.SendMessage(win32con.WM_CHAR, ord(key), 0)
        return True
    except:
        return False

@sio.event
def getWinSize(sid, hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

shell = win32com.client.Dispatch("WScript.Shell")
@sio.event
def setForeground(sid, hwnd):
    shell.SendKeys('%')
    win32gui.SetForegroundWindow(hwnd)
    return True

@sio.event
def connect(sid, environ):
    print(f"connected with {sid}")

@sio.event
def onload(sid):
    hwnd = win32gui.FindWindow(None, "AUTOMATION")
    print(f"browser handle : {hwnd}")

@sio.event
def disconnect(sid):
    print(f"disconnected with {sid}")
    os._exit(1)

@sio.event
def moveMouse(sid, pos, d=0.2):
    mouse.move(pos[0], pos[1], duration=d)
    return True

@sio.event
def findImg(background, target):
    bgImg = b64ToImg(background)
    tgImg = b64decode(target)
    bg = cv2.cvtColor(bgImg, cv2.COLOR_BGR2GRAY)
    tg = cv2.cvtColor(tgImg, cv2.COLOR_BGR2GRAY)
    w, h = tg.shape[::-1]
    res = cv2.matchTemplate(bg, tg, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc,max_loc = cv2.minMaxLoc(res)
    acc = max_val
    x = max_loc[0]+(tg.shape[1]/2)
    y = max_loc[1]+(tg.shape[0]/2)
    return acc, x, y

signal.signal(signal.SIGINT, signalHandler)
path = os.getcwd()
os.system(f"start msedge --app={path}\\index.html")
web.run_app(app, host="localhost", port=8080)
