import socket, base64, cv2
import numpy as np
import warnings
warnings.simplefilter("ignore", DeprecationWarning)


IP = "192.168.0.196"
PORT = 12342

SERVER = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SERVER.bind((IP, PORT))

read = False
imgAry = []

while True:
        data_b, addr = SERVER.recvfrom(10240)
        data_str = data_b.decode() #byte -> str
        if data_str == "break":
                break
        data = data_str.split("|")

        imgAry.insert(int(data[0]), data[2])
        if data[0] == data[1]:
                data_sum = "".join(imgAry)
                try:
                        img = cv2.imdecode(np.fromstring(base64.b64decode(data_sum), np.uint8), cv2.IMREAD_COLOR)
                        cv2.imshow('img', img)
                        cv2.waitKey(1)
                        imgAry = []
                except:
                        print("error")
        
cv2.destroyAllWindows()
