from flask import Flask, Response
from flask_cors import CORS
import argparse
import serial

parser = argparse.ArgumentParser()
parser.add_argument("--com", nargs=None, type=str, required=True)
parser.add_argument("--port", nargs=None, type=int, required=True)
args = parser.parse_args()

com = args.com
port = args.port

ser = serial.Serial(port=com, baudrate=9600)
print(f"{com}에 연결되었습니다.")

app = Flask(__name__)
CORS(app)

@app.route("/<cmd>")
def get_input(cmd):
    try: ser.write(cmd.encode())
    except: print("serial failed")
    return Response(status=204)

@app.route("/check")
def check():
    return "OK"

app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)