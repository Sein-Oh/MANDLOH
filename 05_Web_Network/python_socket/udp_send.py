import cv2, base64, math
import numpy as np
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cap = cv2.VideoCapture("wild.mp4")

while True:
	ret, frame = cap.read()
	frame = cv2.resize(frame, dsize=(320, 240), interpolation=cv2.INTER_AREA)	
	cv2.imshow('frame', frame)
	
	k = cv2.waitKey(30) & 0xff
	if k == ord('q'):
		ret, jpeg = cv2.imencode('.jpg', frame)
		jpeg = base64.b64encode(jpeg.tobytes())
		jpeg_str = jpeg.decode()
		count = math.ceil(len(jpeg_str)/1000)
		
		for i in range(0, count):
			#chunk = jpeg.decode()[i*count:(i+1)*count].encode()			
			#chunk = jpeg_str[0:1024].encode()
			chunk_str = str(i).rjust(2,"0") + "|" + str(count) + "|" + jpeg_str[i*1000:(i+1)*1000]
			chunk = chunk_str.encode()
			sock.sendto(chunk, ('localhost', 8080))
			cv2.waitKey(1)
		break
	
cv2.destroyAllWindows()
cap.release()
