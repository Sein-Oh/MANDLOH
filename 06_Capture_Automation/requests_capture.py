import cv2
import requests
import numpy as np


class MJPEGCapture:
    def __init__(self, url):
        self.response = requests.get(url, stream=True)
        self.stream = self.response.iter_content(chunk_size=32768)
        self.buffer = b''

    def read(self):
        while True:
            try:
                self.buffer += next(self.stream)

                start = self.buffer.find(b'\xff\xd8')
                end = self.buffer.find(b'\xff\xd9')

                if start != -1 and end != -1 and end > start:
                    jpg = self.buffer[start:end + 2]
                    self.buffer = self.buffer[end + 2:]

                    frame = cv2.imdecode( np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                    if frame is not None:
                        return True, frame

            except Exception:
                return False, None

    def release(self):
        self.response.close()