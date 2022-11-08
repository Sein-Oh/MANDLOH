import base64
import cv2
import numpy as np
import PySimpleGUI as sg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
import threading
import time

class setInterval(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)

def getImage(query, width, height):
    script = f"""
        const video = document.querySelector("{query}");
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

def getSize(query):
    script = f"""
    const video = document.querySelector("{query}");
    return [video.videoWidth, video.videoHeight];
    """
    width, height = driver.execute_script(script)
    return [width, height]

def showImage():
    img = getImage("video", 1280, 720)
    cv2.imshow("img", img)
    cv2.waitKey(0)

def findVideo():
    try: return driver.find_elements(By.TAG_NAME, "video")[0]
    except: return False


print("앱을 실행합니다.")
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Edge(options=options)
driver.get("https://lineage2m.plaync.com/webplay/linw")

print("스트리밍을 완료하세요.", end="", flush=True)
while not findVideo():
    print(".", end="", flush=True)
    time.sleep(1)
print("완료했습니다.")
