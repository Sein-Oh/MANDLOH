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

# 이미지 찾기 함수
def find_img(background, target, threshold):
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    res = np.where(res>=threshold) # res에서 threshold보다 큰 값만 취한다.
    point = []
    for pt in zip(*res[::-1]):
        point.append(pt)
    print(point)
    return len(point) # 찾음여부만 확인하기 위해 길이로 리턴한다.

def addImage(background, foreground, x, y):
    ret, mask = cv2.threshold(foreground[:,:,3], 1, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)
    foreground = cv2.cvtColor(foreground, cv2.COLOR_BGRA2BGR)
    h, w = foreground.shape[:2]
    roi = background[y:y+h, x:x+w]
    maskedFg = cv2.bitwise_and(foreground, foreground, mask=mask)
    maskedBg = cv2.bitwise_and(roi, roi, mask=mask_inv)
    added = maskedFg + maskedBg
    background[y:y+h, x:x+w] = added
    return background

def resize(img, width, height):
    h, w, c = img.shape
    ratio = height / h if h > w else width / w
    resized_img = cv2.resize(img, dsize=(int(w*ratio),int(h*ratio)), interpolation=cv2.INTER_LINEAR)
    rh, rw, rc = resized_img.shape
    x = int(abs((width-rw)/2))
    y = int(abs((height-rh)/2))
    fore_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2BGRA) #4 channel
    back = np.zeros((height, width, 3), np.uint8) #3 channel
    result = addImage(back, fore_img, x, y)
    return result


