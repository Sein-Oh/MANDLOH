from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import PySimpleGUI as sg
import cv2
import numpy as np
import base64
import time

def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)

driver = False
def checkBrowser():
    if driver != False:
        log = driver.get_log("driver")
        if len(log):
            print(log[-1])
            return False
    else:
        return None

def killDriver():
    if driver != False:
        print("프로그램을 종료합니다.")
        driver.quit()

def getImage(width, height):
    script = f"""
        const video = document.querySelector("video");
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        canvas.width = {width};
        canvas.height = {height};
        ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/webp");
    """
    data = driver.execute_script(script)
    img = b64ToImg(data)
    return img


layout = [
    [sg.Button("Login", metadata=False), sg.Button("Ready", metadata=False), sg.Button("Start")]
]

window = sg.Window(
    "Button Click",
    layout,
    grab_anywhere=True,
    auto_size_buttons=False,
    default_button_element_size=(12,1),
    use_default_focus=False,
    finalize=True
)

pt = time.time()
while True:
    ct = time.time()
    print(ct - pt)
    pt = ct
    event, values = window.read(timeout=100)
    if event == sg.WINDOW_CLOSED or checkBrowser() == False:
        killDriver()
        break
    elif event == "Login":
        if window["Login"].metadata:
            print("이미 실행한 상태입니다. 재사용 하려면 종료 후 다시 시작하세요.")
        else:
            window["Login"].metadata = True
            print("로그인을 시작합니다. 완료 후 Ready 버튼을 누르세요.")
            driver = webdriver.Edge()
            driver.get("file:///C:/Users/Administrator/Desktop/UI/selenium/index.html")
    elif event == "Ready":
        if not window["Login"].metadata:
            print("로그인 후 사용하세요.")
        else:
            if not window["Ready"].metadata:
                window["Ready"].metadata = True
                print("준비를 완료했습니다.")

    elif event == "Start":
        window["Start"].metadata = True

    if window["Start"].metadata:
        img = getImage(1280, 720)
        # cv2.imshow("img", img)
        # cv2.waitKey(1)


window.close()
