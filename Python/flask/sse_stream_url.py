from flask import Flask, Response
from flask_cors import CORS
import time
import json
from datetime import datetime

import base64
import pybase64
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)
stream_url = "http://127.0.0.1:8000"
input_url = "http://127.0.0.1:8000/input"

cap = cv2.VideoCapture(stream_url)

def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)


def cvToB64(img):
    ret, buffer = cv2.imencode(".png", img)
    buffer_b = buffer.tobytes()
    im_b64 = pybase64.b64encode(buffer_b)
    return str(im_b64)

t_prev = time.time()
def gen_frame():
    global t_prev
    while True:
        clock = datetime.now().time()
        t = f"{clock:%T}"
        ret, frame = cap.read()
        frame = cv2.resize(frame, dsize=(0,0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        if ret:
            frame_b64 = cvToB64(frame)
            data = {"time": t, "imgdata": frame_b64}
            yield f"""event: notice\ndata: {json.dumps(data)}\n\n"""
        t = time.time()
        print(t - t_prev)
        t_prev = t

@app.get("/")
def connection():
    return Response(gen_frame(), content_type="text/event-stream")


if __name__ == "__main__":
    app.run(port=5000)