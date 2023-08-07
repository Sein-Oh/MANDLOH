import cv2
import numpy as np
import base64

def calc_hp(img_hp, thres_min=210):
    #HP 계산 - Red값만 추출해 블러>임계처리 후 가장 밝은값의 위치를 찾는다.
    hpSplit = cv2.split(img_hp)[2]  # hp바의 BGR색상 중 R값만 가져오기
    hpBlur = cv2.blur(hpSplit, (5, 5))  # 블러 처리
    hpThresh = cv2.threshold(hpBlur, thres_min, 255, cv2.THRESH_BINARY)[1]
    
    #배열 중 255 값이 있는 주소를 찾는다. flip처리로 오른쪽 끝을 먼저 찾는다
    hpPoint = np.flip(hpThresh).argmax()
    hpPoint = 100 if hpPoint >= hpThresh.shape[1] else int((1-(np.flip(hpThresh).argmax() / hpThresh.shape[1])) * 100)
    return hpPoint

def cvToB64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = base64.b64encode(buffer_b)
    return str(im_b64)