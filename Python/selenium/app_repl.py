import base64
import cv2
import numpy as np
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import threading

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

def showImage():
    img = getImage("video", 1280, 720)
    cv2.imshow("img", img)
    cv2.waitKey(0)


def checkBrowser():
    log = driver.get_log("driver")
    if len(log): print(log[-1])
    else: print("None")

print("앱을 실행합니다.")
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Edge(options=options)
driver.get("https://sein-oh.github.io/js_capture_screen/")
