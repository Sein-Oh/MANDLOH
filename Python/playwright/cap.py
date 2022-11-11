from playwright.sync_api import sync_playwright
import cv2
import numpy as np
import base64
import time

#base64 이미지를 opencv형식 이미지로
def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)

def getImageScript(width, height):
    script = f"""
    const video = document.querySelector("video");
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = {width};
    canvas.height = {height};
    ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight, 0, 0, canvas.width, canvas.height);
    canvas.toDataURL("image/webp");
    """
    return script

print("앱을 실행합니다.")
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=False, channel="msedge")
context = browser.new_context()
page = context.new_page()
page.goto("https://sein-oh.github.io/js_capture_screen/")

pt= time.time()
while True:
    ct = time.time()
    print(ct-pt)
    pt = ct
    img = b64ToImg(page.evaluate(getImageScript(1280,720)))
    cv2.imshow("img", img)
    key = cv2.waitKey(1)
    if key == ord("q"):
        break

cv2.destroyAllWindows()
playwright.stop()
