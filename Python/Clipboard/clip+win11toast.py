import cv2
import numpy
import dxcam
import pyperclip
import time
from win11toast import notify, toast

#Global variables
show_frame = False

#dxcam setting
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=5)

notify("앱을 시작합니다😀\n사용 방법은 블로그를 참고하세요😊")

pyperclip.copy("")
while True:
    clip = pyperclip.paste()

    if clip == "EXIT":
        notify("앱을 종료합니다😴")
        break

    elif clip == "PAUSE":
        pyperclip.copy("")
        toast("일시 정지🚫\n이 알림을 해제하면 다시 시작됩니다.", scenario="incomingCall", audio={"silent":"true"})

    elif clip == "CHECK":
        pyperclip.copy("")
        notify("앱이 실행 중 입니다👌")
    
    elif clip == "SHOW":
        pyperclip.copy("")
        show_frame = not show_frame
        try: cv2.destroyAllWindows()
        except: pass

    if show_frame:
        frame = cam.get_latest_frame()
        frame = cv2.resize(frame, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
    time.sleep(0.2)

cv2.destroyAllWindows()
