import cv2
import numpy as np

class Gray(object):
	def __init__(self):
		self._x = None
		self._y = None
		print('gray init')
	def cvt(self, img):
		return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

c = Gray()

def onmouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
    	c._x = x
    	c._y = y

cap = cv2.VideoCapture('f22.mp4')
cv2.namedWindow('frame') 
cv2.setMouseCallback('frame', onmouse)

while True:
	ret, frame = cap.read()
	gr = c.cvt(frame)
	cv2.imshow('frame', gr)
	key = cv2.waitKey(30) & 0xff
	print("{}, {}".format(c._x, c._y))
	if key == ord('q'):
		break

cv2.destroyAllWindows()
cap.release()
