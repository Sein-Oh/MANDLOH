from selenium import webdriver
from selenium.webdriver.common.by import By
from skimage.metrics import structural_similarity as ssim
import PySimpleGUI as sg
import cv2
import numpy as np
import base64
import time
import threading
import pickle
import os
import requests

# 스크린샷 폴더 생성
try: os.makedirs("screenshot")
except: pass


#쿨타임 계산용 딕셔너리
coolTime = {"home": False, "pk": False, "timer1": False, "timer2": False, "timer3": False}

#base64 이미지를 opencv형식 이미지로
def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)

#셀레니움 브라우저 확인
def checkBrowser():
    if driver != False:
        log = driver.get_log("driver")
        if len(log):
            print(log[-1])
            return False
    else:
        return None

#셀레니움 드라이버 종료
def killDriver():
    if driver != False:
        print("프로그램을 종료합니다.")
        driver.quit()


#파일저장에 날짜 및 시간 넣기. MMDDHHMMSS 형식
def timeStamp():
    now = time.localtime()
    text = f"{str(now.tm_mon).zfill(2)}{str(now.tm_mday).zfill(2)}_{str(now.tm_hour).zfill(2)}{str(now.tm_min).zfill(2)}{str(now.tm_sec).zfill(2)}"
    return text

#브라우저에서 이미지 데이터 가져오기
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

# 틀린그림 찾기
def subImg(origin, target):
    origin_gray = cv2.cvtColor(origin, cv2.COLOR_BGR2GRAY)
    target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    (score, diff) = ssim(origin_gray, target_gray, full=True)
    return score

#쿨타임 초기화용 함수
def coolDown(key):
    global coolTime
    coolTime[key] = False
    print("{}의 쿨타임 종료.".format(key))

#쿨타임 적용
def coolRun(key, sec):
    global coolTime
    coolTime[key] = True
    threading.Timer(sec, coolDown, [key]).start()

#키 입력
def sendKey(key, count=1, delay=0):
    for i in range(count):
        try:
            element.send_keys(key)
        except:
            print("키입력 실패.")
        if i < count-1: time.sleep(delay)

#텔레그램으로 이미지 보내기
def sendPhoto(token, id, imgPath, caption):
    data = {"chat_id": id, "caption": caption}
    url = f"https://api.telegram.org/bot{token}/sendphoto?chat_id={id}"
    with open(imgPath, "rb") as f:
        requests.post(url, data=data, files={"photo": f})

#텔레그램 메시지 보내기
def sendMessage(token, id, msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={id}&text={msg}"
    requests.get(url)

#이미지 저장. 텔레그램 연동
def saveImg(img):
    file_name = f"screenshot/{timeStamp()}.jpg"
    cv2.imwrite(file_name, img)
    if window["telegram"].get():
        token = window["token"].get()
        id = window["room_id"].get()
        sendPhoto(token, id, file_name, "캡처")
####################### FUNCTION ############################
#############################################################
driver = False
toggle_off = b"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"
toggle_on = b"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"
img_potion_empty = b64ToImg("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAAAXNSR0IArs4c6QAAAjdJREFUKFMdkE1LVGEAhZ/3fjj3Xp0740zmlBsx8gPTmHIRFAW1EaMpLapFQYSraNUmSGiRVrZpUwuhQCikiIJq4aIW/YGg2oY05pgbp5zr6NyZ+/G+4Zz94XnOEc8eXFcmCj2OCfw6cayQCqQEwzCw7ASNKES3LaSuEUkQL2YnVRJFolqltPSLQOpUvCpKgpt0SNoGbkeW2HWpJxKsV2uIN9PX1MbSTyzPwxQGxXKVOx8WQSkeX5xgb7IFYYDvtCIzGUq1BuL1zdMqWF3GajQw29r5uuYxs/iZndwrjDKQNsGv0tB1okyWWm4PYq4wrLJBDVuDTWnw3ZM8+vQFUEyNnqLfinAJiQDfTRH19yPmC8MqpwJMTeC3tPHDi5h697Gp9/B8gX1mQFqEhHFM2TAw8ocRrybyyt320DRBYCVZxeHG/AKUVnhy+xY5tUUiqKFpGp5lU+vtQyyM51Vqu4KUMYFps2EkmZyZpb5c5OXcUzq0ADP0mxsrCQu/dwDxfHxEdcoGpgzxlcZaZFAqexi6Rk9nlix1zLhBoGiSoh3SlV5XHd/fTVbWkZrBt3KN+80jYObsGAczFnpUJ7RbWQlC2g/lEZdHulWP69CXdhBCo7gVcvft+2Zp+sI5uswIXUh8yyFKpcgNDSKujh1R0abHxu8iI0ODOJZDHMcoqbASBokWjeKfEnbnbnoODGKnXcSlM8eUkJJ4u8bW33XCyj80GSNjST2KOHryBLu6cphJB63FwLEt/gPkt/XajD1j6gAAAABJRU5ErkJggg==")
img_pk_state = b64ToImg("data:image/png;base64,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")
res_potion = 0
res_pk = 0

sg.theme("Default1")
text_size = (12,1)
btn_off = ("gray", sg.theme_button_color_background())
btn_on = (sg.theme_button_color_text(), sg.theme_button_color_background())

viewer = [
    [sg.Text("HP:미확인", key="lbl_hp", size=(10, None)), sg.Image(size=(200, 6), key="img_hp")],
    [sg.Text("MP:미확인", key="lbl_mp", size=(10, None)), sg.Image(size=(200, 6), key="img_mp")],
]

prepare = [
    [sg.Button("로그인", key="login", metadata=False), sg.Button("캡처시작", key="capture", metadata=False), sg.Button("가방열기", key="inven"), sg.Button("설정저장", key="save")]
]

control = [
    [sg.Text("실행"), sg.Im(toggle_off, key='run', enable_events=True , metadata=False)],
    [sg.Checkbox("자동귀환", key="home_use"), sg.Checkbox("물약오링 귀환", key="home_potion_use"), sg.Checkbox("전투대응", key="pk_use")],
    [sg.Checkbox("타이머1", key="t1_use"), sg.Checkbox("타이머2", key="t2_use"), sg.Checkbox("타이머3", key="t3_use")]
]

telegram = [
    [sg.Checkbox("텔레그램 알림", key="telegram", enable_events=True)],
    [sg.Text("토큰"), sg.Input(key="token", expand_x=True)],
    [sg.Text("채팅번호"), sg.Input(key="room_id", expand_x=True)]
]

home = [
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("0", justification="center", key="home_hp_min"), sg.Text("~"), sg.Input("30", justification="center", key="home_hp_max")],
    [sg.Text("재사용시간", size=text_size), sg.Input("0", justification="center", key="home_cool")],
    [sg.Text("입력키", size=text_size), sg.Input("8", justification="center", key="home_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("4", justification="center", key="home_count")],
    [sg.Text("입력횟수딜레이", size=text_size), sg.Input("0.5", justification="center", key="home_delay")]
]

pkaction = [
    [sg.Text("입력키", size=text_size), sg.Input("7", justification="center", key="pk_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("4", justification="center", key="pk_count")],
    [sg.Text("입력횟수딜레이", size=text_size), sg.Input("0.5", justification="center", key="pk_delay")],
    [sg.Text("입력대기시간", size=text_size), sg.Input("0", justification="center", key="pk_wait")],
    [sg.Text("재사용시간", size=text_size), sg.Input("5", justification="center", key="pk_cool")],
]

timer1 = [
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("31", justification="center", key="t1_hp_min"),sg.Text("~"), sg.Input("80", justification="center", key="t1_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("10", justification="center", key="t1_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t1_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("4", justification="center", key="t1_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("1", justification="center", key="t1_count")],
    [sg.Text("입력횟수딜레이", size=text_size), sg.Input("0.5", justification="center", key="t1_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("1", justification="center", key="t1_cool")]
]

timer2 = [
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("31", justification="center", key="t2_hp_min"),sg.Text("~"), sg.Input("50", justification="center", key="t2_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("0", justification="center", key="t2_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t2_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("7", justification="center", key="t2_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("2", justification="center", key="t2_count")],
    [sg.Text("입력횟수딜레이", size=text_size), sg.Input("0.5", justification="center", key="t2_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("5", justification="center", key="t2_cool")]
]

timer3 = [
    [sg.Text("사용구간(HP)", size=text_size), sg.Input("0", justification="center", key="t3_hp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t3_hp_max")],
    [sg.Text("사용구간(MP)", size=text_size), sg.Input("0", justification="center", key="t3_mp_min"),sg.Text("~"), sg.Input("100", justification="center", key="t3_mp_max")],
    [sg.Text("입력키", size=text_size), sg.Input("f", justification="center", key="t3_key")],
    [sg.Text("입력횟수", size=text_size), sg.Input("1", justification="center", key="t3_count")],
    [sg.Text("입력횟수딜레이", size=text_size), sg.Input("0.5", justification="center", key="t3_delay")],
    [sg.Text("재사용시간", size=text_size), sg.Input("0.2", justification="center", key="t3_cool")]
]

layout = [
    [sg.Frame("모니터링", viewer, expand_x=True)],
    [sg.Frame("실행준비", prepare, expand_x=True)],
    [sg.Frame("제어", control, expand_x=True)],
    [sg.Frame("설정", [[sg.TabGroup([[sg.Tab("자동귀환", home), sg.Tab("전투대응", pkaction), sg.Tab("타이머1", timer1), sg.Tab("타이머2", timer2), sg.Tab("타이머3", timer3)]], expand_x=True)]], expand_x=True)],
    [sg.Frame("텔레그램", telegram, expand_x=True)],
    [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]

window = sg.Window(
    "Lineage W",
    layout,
    grab_anywhere=True,
    auto_size_buttons=False,
    default_button_element_size=(8, 1),
    default_element_size=(3, 1),
    use_default_focus=False,
    finalize=True
)

#설정 불러오기
try:
    print("저장된 자료를 불러옵니다.")
    with open("userdata.pickle", "rb") as f:
        data = pickle.load(f)
        for key in data.keys():
            window[key].update(data[key])
except:
    print("불러오기에 실패했습니다.")

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
            print("로그인을 시작합니다.")
            driver = webdriver.Edge()
            driver.get("https://lineage2m.plaync.com/webplay/linw")

    elif event == "capture":
        if window["login"].metadata == False:
            print("로그인 후 시도하세요.")
        else:
            window["capture"].metadata = True
            print("캡처를 시작합니다.")
            element = driver.find_elements(By.TAG_NAME, "video")[0]

    elif event == "inven":
        sendKey("i")

    elif event == "run":
        #run 버튼의 메타데이터를 바꾸고 이를 이용해 이미지를 토글한다.
        window["run"].metadata = not window["run"].metadata
        if window["run"].metadata:
            print("앱을 실행합니다.")
            window["run"].update(toggle_on)
        else:
            print("앱 실행을 중지합니다.")
            window["run"].update(toggle_off)
    
    elif event == "save":
        data = {}
        for el in window.element_list():
            key = el.Key
            if el.Type == "input" or el.Type == "checkbox":
                data[key] = window[key].get()
        with open("userdata.pickle", "wb") as f:
            pickle.dump(data, f)
            print("설정을 userdata.pickle에 저장했습니다.")

    elif event == "telegram":
        if window["telegram"].get():
            sendMessage(window["token"].get(), window["room_id"].get(), "텔레그램 알림을 시작합니다.")

    if window["capture"].metadata:
        #브라우저에서 1280x720크기로 이미지 받아오기
        full_img = getImage(1280, 720)

        #HP/MP부분 잘라내기
        img_hp = full_img[32:38, 90:280]  # y1:y2,x1:x2
        img_mp = full_img[45:51, 90:280]  # y1:y2,x1:x2
        #HP/MP이미지 갱신하기
        window["img_hp"].update(data=cv2.imencode(".png", img_hp)[1].tobytes())
        window["img_mp"].update(data=cv2.imencode(".png", img_mp)[1].tobytes())

        #HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
        hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
        hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
        hpThresh = cv2.threshold(hpBlur, 210, 255, cv2.THRESH_BINARY)[1]
        
        #배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
        hpPoint = np.flip(hpThresh).argmax()
        if hpPoint >= hpThresh.shape[1]:
            hpPoint = 100
        else:
            hpPoint = int((1-(np.flip(hpThresh).argmax() / hpThresh.shape[1])) * 100)

        #MP 계산        
        mpBlue = img_mp[:,:,0]
        mpThresh = cv2.threshold(mpBlue, 170, 255, cv2.THRESH_BINARY)[1] # 임계처리. 170 이상만 255로 치환
        mpPoint = int((1-(np.flip(mpThresh).argmax()/mpThresh.shape[1])) * 100)

        window["lbl_hp"].update("HP :{}%".format(hpPoint))  # 라벨 업데이트
        window["lbl_mp"].update("MP :{}%".format(mpPoint))  # 라벨 업데이트

        #포션이미지 잘라내고 비교하기
        img_potion = full_img[635:648, 472:485]
        res_potion = subImg(img_potion, img_potion_empty)

        #PK이미지 잘라내고 비교하기
        img_pk = full_img[533:558, 1057:1082]
        res_pk = subImg(img_pk, img_pk_state)


    # 실행
    if window["run"].metadata:
        if window["home_use"].get():
            try:
                min = int(window["home_hp_min"].get())
                max = int(window["home_hp_max"].get())
                cool = float(window["home_cool"].get())
                key = window["home_key"].get()
                count = int(window["home_count"].get())
                delay = float(window["home_delay"].get())

                if hpPoint >= min and hpPoint <= max and coolTime["home"] == False:
                    print("귀환을 사용합니다.")
                    sendKey(key, count, delay)
                    saveImg(full_img)
                    if cool == 0.0:
                        window["run"].metadata = False
                        window["run"].update(toggle_off)
                    else: coolRun("home", cool)

            except: print("자동귀환 설정 불러오기에 실패했습니다.")

        if window["home_potion_use"].get():
            if res_potion > 0.9:
                print("귀환을 사용합니다.")
                key = window["home_key"].get()
                sendKey(key, 1, 0)
                saveImg(full_img)
                window["run"].metadata = False
                window["run"].update(toggle_off)

        if window["pk_use"].get() and coolTime["pk"] == False:
            if res_pk > 0.9:
                print("전투대응을 사용합니다.")
                key = window["pk_key"].get()
                count = int(window["pk_count"].get())
                delay = float(window["pk_delay"].get())
                wait = float(window["pk_wait"].get())
                cool = float(window["pk_cool"].get())
                threading.Timer(wait, sendKey, [key, count, delay])
                saveImg(full_img)
                coolRun("pk", cool)
    
        if window["t1_use"].get():
            try:
                hp_min = int(window["t1_hp_min"].get())
                hp_max = int(window["t1_hp_max"].get())
                mp_min = int(window["t1_mp_min"].get())
                mp_max = int(window["t1_mp_max"].get())
                key = window["t1_key"].get()
                count = int(window["t1_count"].get())
                delay = float(window["t1_delay"].get())
                cool = float(window["t1_cool"].get())

                if hpPoint >= hp_min and hpPoint <= hp_max and mpPoint >= mp_min and mpPoint <= mp_max and coolTime["timer1"] == False:
                    print("타이머1을 사용합니다.")
                    sendKey(key, count, delay)
                    coolRun("timer1", cool)
            except:
                print("타이머1 설정 불러오기에 실패했습니다.")

        if window["t2_use"].get():
            try:
                hp_min = int(window["t2_hp_min"].get())
                hp_max = int(window["t2_hp_max"].get())
                mp_min = int(window["t2_mp_min"].get())
                mp_max = int(window["t2_mp_max"].get())
                key = window["t2_key"].get()
                count = int(window["t2_count"].get())
                delay = float(window["t2_delay"].get())
                cool = float(window["t2_cool"].get())

                if hpPoint >= hp_min and hpPoint <= hp_max and mpPoint >= mp_min and mpPoint <= mp_max and coolTime["timer2"] == False:
                    print("타이머2을 사용합니다.")
                    sendKey(key, count, delay)
                    coolRun("timer2", cool)
            except:
                print("타이머2 설정 불러오기에 실패했습니다.")

        if window["t3_use"].get():
            try:
                hp_min = int(window["t3_hp_min"].get())
                hp_max = int(window["t3_hp_max"].get())
                mp_min = int(window["t3_mp_min"].get())
                mp_max = int(window["t3_mp_max"].get())
                key = window["t3_key"].get()
                count = int(window["t3_count"].get())
                delay = float(window["t3_delay"].get())
                cool = float(window["t3_cool"].get())

                if hpPoint >= hp_min and hpPoint <= hp_max and mpPoint >= mp_min and mpPoint <= mp_max and coolTime["timer3"] == False:
                    print("타이머3을 사용합니다.")
                    sendKey(key, count, delay)
                    coolRun("timer3", cool)
            except:
                print("타이머3 설정 불러오기에 실패했습니다.")

window.close()
