from flask import Flask, Response
from flask_cors import CORS
import argparse
import cv2
import dxcam
import io

parser = argparse.ArgumentParser()
parser.add_argument("--port", nargs=None, type=str, required=True)
args = parser.parse_args()

port = args.port

app = Flask(__name__)
CORS(app)

#화면캡처 생성
cam = dxcam.create(output_color="BGR")
cam.start(target_fps=10)

#스트리밍 구현부
def gen():
    while True:
        frame = cam.get_latest_frame()
        # frame = cv2.resize(frame, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

#라우팅 구성
@app.route('/')
def video_feed():
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/check")
def check():
    return "OK"

app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)
