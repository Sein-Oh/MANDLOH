import serial
import time

class Serial:
    def __init__(self, port="COM9", baudrate=9600):
        self.port = port
        self.ser = serial.Serial(port=self.port, baudrate=baudrate)
        print(f"{self.port}로 시리얼이 연결되었습니다.")

    def send(self, keys, delay=1.2):
        ary = keys.split(",")
        l = len(ary)
        if l > 1:
            for idx, key in enumerate(ary):
                self.ser.write(key.encode())
                if idx + 1 != l:
                    time.sleep(delay)
                idx += 1
        else:
            self.ser.write(ary[0].encode())