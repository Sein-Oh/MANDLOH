from flask import Flask, request
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)

def b64ToImg(data):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)


@app.route("/say/<msg>")
@cross_origin()
def say(msg):
    print(msg)
    return "Done"

@app.route('/post', methods=['POST']) #post echo api
@cross_origin()
def post_echo_call():
    param = request.get_json()
    print(param)
    return "OKOK"

if __name__ == '__main__':
    app.run("localhost", port=8080)
