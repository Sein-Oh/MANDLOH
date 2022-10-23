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


text_size = (10,1)
sg.theme("Dark")
control = [
    [sg.Button("로그인", key="login", metadata=False), sg.Button("가방열기", key="inven")],
    [sg.Button("실행", key="run"), sg.Button("중지", key="stop")]
]

viewer = [
    [sg.Image(size=(200, 6), key="img_hp"), sg.Text("HP:%", key="lbl_hp")],
    [sg.Image(size=(200, 6), key="img_mp"), sg.Text("MP:%", key="lbl_mp")]
]


home = [
    [sg.Checkbox("사용", key="home_use"), sg.Checkbox("물약오링 귀환", key="home_potion_use")],
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("0", justification="center", key="home_hp_min"), sg.Text("~"), sg.Input("30", justification="center", key="home_hp_max")],
    [sg.Text("재사용시간", size=text_size), sg.Input("0", justification="center", key="home_cool")],
    [sg.Text("입력키", size=text_size), sg.Input("8", justification="center", key="home_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("4", justification="center", key="home_count")],
    [sg.Text("입력딜레이", size=text_size), sg.Input("0.5", justification="center", key="home_delay")]
]

pkaction = [
    [sg.Checkbox("사용")],
    [sg.Text("입력키", size=text_size), sg.Input("7", justification="center", key="pk_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("4", justification="center", key="pk_count")],
    [sg.Text("입력딜레이", size=text_size), sg.Input("0.5", justification="center", key="pk_delay")],
    [sg.Text("입력대기시간", size=text_size), sg.Input("0", justification="center", key="pk_wait")],
    [sg.Text("재사용시간", size=text_size), sg.Input("5", justification="center", key="pk_cool")],
]

timer1 = [
    [sg.Checkbox("사용", key="t1_use")],
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("31", justification="center", key="t1_hp_min"),sg.Text("~"), sg.Input("50", justification="center", key="t1_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("0", justification="center", key="t1_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t1_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("7", justification="center", key="t1_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("2", justification="center", key="t1_count")],
    [sg.Text("입력딜레이", size=text_size), sg.Input("0.5", justification="center", key="t1_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("5", justification="center", key="t1_cool")]
]

timer2 = [
    [sg.Checkbox("사용", key="t2_use")],
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("51", justification="center", key="t2_hp_min"),sg.Text("~"), sg.Input("80", justification="center", key="t2_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("10", justification="center", key="t2_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t2_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("4", justification="center", key="t2_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("1", justification="center", key="t2_count")],
    [sg.Text("입력딜레이", size=text_size), sg.Input("0.5", justification="center", key="t2_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("3", justification="center", key="t2_cool")]
]

timer3 = [
    [sg.Checkbox("사용", key="t3_use")],
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("0", justification="center", key="t3_hp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t3_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("0", justification="center", key="t3_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t3_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("f", justification="center", key="t3_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("1", justification="center", key="t3_count")],
    [sg.Text("입력딜레이", size=text_size), sg.Input("0.5", justification="center", key="t3_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("0.2", justification="center", key="t3_cool")]
]

layout = [
    [sg.Frame("제어", control), sg.Frame("모니터링", viewer)],
    [sg.Frame("자동귀환", home), sg.Frame("전투대응", pkaction)],
    [sg.Frame("타이머1", timer1), sg.Frame("타이머2", timer2), sg.Frame("타이머3", timer3)],
    [sg.Multiline(size=(None, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]

window = sg.Window(
    "Button Click",
    layout,
    grab_anywhere=True,
    auto_size_buttons=False,
    default_button_element_size=(10, 1),
    default_element_size=(3, 1),
    use_default_focus=False,
    finalize=True
)

while True:
    event, values = window.read(timeout=100)
    if event == sg.WINDOW_CLOSED or checkBrowser() == False:
        killDriver()
        break
    elif event == "login":
        if window["login"].metadata:
            print("이미 실행한 상태입니다. 재사용 하려면 종료 후 다시 시작하세요.")
        else:
            window["login"].metadata = True
            print("로그인을 시작합니다. 완료 후 Ready 버튼을 누르세요.")
            driver = webdriver.Edge()
            driver.get("https://lineage2m.plaync.com/webplay/linw")

    elif event == "run":
        if window["login"].metadata == False:
            print("로그인 후 가능합니다.")
        else:
            window["run"].metadata = not window["run"].metadata

    if window["run"].metadata:
        #브라우저에서 1280x720크기로 이미지 받아오기
        full_img = getImage(1280, 720)
        #HP/MP부분 잘라내기
        img_hp = full_img[32:38, 90:280]  # y1:y2,x1:x2
        img_mp = full_img[45:51, 90:280]  # y1:y2,x1:x2
        #HP/MP이미지 갱신하기
        window["img_hp"].update(data=cv2.imencode(".png", img_hp)[1].tobytes())
        window["img_mp"].update(data=cv2.imencode(".png", img_mp)[1].tobytes())

        # HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
        hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
        hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
        hpThresh = cv2.threshold(hpBlur, 222, 255, cv2.THRESH_BINARY)[
            1]  # 임계처리 222 이상만 255로 치환
        # 배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
        hpPoint = np.flip(hpThresh).argmax()
        if hpPoint >= hpThresh.shape[1]:
            hpPoint = 100
        else:
            hpPoint = int(
                (1-(np.flip(hpThresh).argmax() / hpThresh.shape[1])) * 100)

        # MP 계산
        mpHSV = cv2.cvtColor(img_mp, cv2.COLOR_BGR2HSV)  # 색추출을 위해 HSV로 변환한다.
        blueLower = (120-30, 30, 30)
        blueUpper = (120-10, 255, 255)
        mpSplit = cv2.inRange(mpHSV, blueLower, blueUpper)  # 범위안의 값만 뽑아온다.
        mpBlur = cv2.blur(mpSplit, (3, 3))
        mpThresh = cv2.threshold(mpBlur, 170, 255, cv2.THRESH_BINARY)[
            1]  # 임계처리. 170 이상만 255로 치환
        mpPoint = int((1-(np.flip(mpThresh).argmax()/mpThresh.shape[1])) * 100)

        window["lbl_hp"].update("HP :{}%".format(hpPoint))  # 라벨 업데이트
        window["lbl_mp"].update("MP :{}%".format(mpPoint))  # 라벨 업데이트

window.close()
