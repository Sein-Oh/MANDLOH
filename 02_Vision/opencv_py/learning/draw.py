import cv2, os
import numpy as np

img_save_path = "./img/"
if not os.path.exists(img_save_path):
  os.mkdir(img_save_path)

onDown = False
xprev, yprev = None, None
def onmouse(event, x, y, flags, params):
    global onDown, img, xprev, yprev
    if event == cv2.EVENT_LBUTTONDOWN:
        print("DOWN : {0}, {1}".format(x,y))
        onDown = True
    elif event == cv2.EVENT_MOUSEMOVE:
        if onDown == True:
            print("MOVE : {0}, {1}".format(x,y))
            cv2.line(img, (xprev,yprev), (x,y), (255,255,255), 5)
    elif event == cv2.EVENT_LBUTTONUP:
        print("UP : {0}, {1}".format(x,y))
        onDown = False
    xprev, yprev = x,y

cv2.namedWindow("image")
cv2.setMouseCallback("image", onmouse)
width, height = 280, 280
img = np.zeros((280,280,3), np.uint8)
figNum = 1
while True:
    cv2.imshow("image", img)
    key = cv2.waitKey(1)
    if key == ord('r'):
        img = np.zeros((280,280,3), np.uint8)
        print("Clear.")
    if key == ord('s'):
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_save = cv2.resize(img_gray, dsize=(28,28), interpolation=cv2.INTER_AREA)
        cv2.imwrite("{0}image{1}.jpg".format(img_save_path, str(figNum).zfill(2)), img_save)
        figNum = figNum + 1
        print("Image saved")
    if key == ord('q'):
        print("Good bye")
        break

cv2.destroyAllWindows()