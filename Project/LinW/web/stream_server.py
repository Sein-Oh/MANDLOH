#!/usr/bin/env python
from flask import Flask, Response
import io
import cv2
import dxcam
import time

app = Flask(__name__)
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=5)

t_prev = time.time()

def gen():
    global t_prev
    while True:
        t = time.time() - t_prev
        print(t)
        t_prev = t
        frame = cam.get_latest_frame()
        # frame = cv2.resize(frame, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')


@app.route('/')
def video_feed():
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


if __name__ == '__main__':
    app.run(host="localhost", port=8000, debug=True, threaded=True)
