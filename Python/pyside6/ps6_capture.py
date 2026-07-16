# ps6_capture.py
import cv2
import numpy as np
import requests

class MJPEGCapture:
    """Termux 등 FFmpeg 백엔드가 없을 때 requests를 사용하여 MJPEG을 직접 파싱하는 클래스"""
    def __init__(self, url, timeout=5):
        self.url = url
        self.timeout = timeout
        self.response = None
        self.stream = None
        self.buffer = bytearray()
        self._connect()

    def _connect(self):
        try:
            self.response = requests.get(self.url, stream=True, timeout=self.timeout)
            self.stream = self.response.iter_content(chunk_size=65536)
        except Exception:
            self.stream = None

    def isOpened(self):
        return self.stream is not None

    def read(self):
        if not self.stream:
            return False, None
        while True:
            try:
                start = self.buffer.find(b'\xff\xd8')
                if start != -1:
                    if start > 0:
                        del self.buffer[:start]
                    end = self.buffer.find(b'\xff\xd9', 2)
                    if end != -1:
                        jpg_data = self.buffer[:end + 2]
                        del self.buffer[:end + 2]
                        frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return True, frame
                else:
                    if len(self.buffer) > 1:
                        del self.buffer[:-1]

                chunk = next(self.stream)
                self.buffer.extend(chunk)
            except (StopIteration, Exception):
                return False, None

    def release(self):
        if self.response:
            self.response.close()


class Ps6Capture:
    """
    OpenCV와 Custom MJPEG을 통합한 캡처 클래스
    
    :param mode: 0 (웹캠 인덱스) 또는 "http://..." (스트리밍 URL)
    :param requests: True 설정 시 requests 기반 MJPEG 파싱 모드 활성화 (Termux용)
    """
    def __init__(self, mode, requests=False):
        self.use_requests = requests
        
        if self.use_requests:
            self.cap = MJPEGCapture(mode)
        else:
            self.cap = cv2.VideoCapture(mode)

    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()