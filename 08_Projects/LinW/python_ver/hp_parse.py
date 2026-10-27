import argparse
import os
import requests
import cv2
import numpy as np
import threading
import time

def calc_hp(img_hp, thres_min=210):
    #HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
    hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
    hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
    hpThres = cv2.threshold(hpBlur, thres_min, 255, cv2.THRESH_BINARY)[1]
    #배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
    hpPoint = np.flip(hpThres).argmax()
    hpPoint = 100 if hpPoint >= hpThres.shape[1] else int((1-(np.flip(hpThres).argmax() / hpThres.shape[1])) * 100)
    return hpPoint

def cool_down():
    global cooling
    cooling = False

def cool_run(cooltime):
    global cooling
    cooling = True
    threading.Timer(cooltime, cool_down).start()


parser = argparse.ArgumentParser()
parser.add_argument("--roi", nargs=4, type=int, required=True)
parser.add_argument("--thres", nargs=None, type=int, required=True, default=210)
parser.add_argument("--range", nargs=2, type=int, required=True)
parser.add_argument("--key", nargs="*", type=str, required=True)
parser.add_argument("--cooltime", nargs=None, type=float, required=True)
parser.add_argument("--stream_url", nargs=None, type=str, required=True)
parser.add_argument("--input_url", nargs=None, type=str, required=True)
parser.add_argument("--show", nargs=None, type=bool, required=False, default=False)
args = parser.parse_args()

stream_url = args.stream_url
if "http://" not in stream_url:
    stream_url = "http://" + stream_url

cap = cv2.VideoCapture(stream_url)
ret, frame = cap.read()
if ret == False:
    print("Stream server is not responding.")
    print("")
    os._exit(1)

input_url = args.input_url
if "http://" not in input_url:
    input_url = "http://" + input_url

x1,y1,x2,y2 = args.roi
thres = args.thres
min_hp, max_hp = args.range
key = args.key
cooltime = args.cooltime
cooling = False

while True:
    ret, frame = cap.read()
    roi = frame[y1:y2, x1:x2]
    hp = calc_hp(roi, thres)
    if cooling == False:
        if hp >= min_hp and hp <= max_hp:
            cool_run(cooltime)
            for k in key:
                if "-" in k:
                    t = float(k[1:])
                    time.sleep(t)
                else:
                    try:
                        requests.get(f"{input_url}/{key}", timeout=0.2)
                    except requests.exceptions.Timeout:
                        print(f"Input server is not responding. Key: {k}")

    if args.show == True:
        cv2.imshow("roi", roi)
    cv2.waitKey(200)

