from flask import Flask, Response, request
from flask_cors import CORS
import datetime
import keyboard
import mouse


app = Flask(__name__)
CORS(app)

host = '0.0.0.0'
port = 8000


@app.route('/input', methods=['GET'])
def hello():
    #http://127.0.0.1:8000/input?cmd=click&x=30&y=50
    cmd = request.args.get('cmd', type=str)
    
    if cmd == 'check':
        return 'ok'
    
    elif cmd == 'click':
        x = request.args.get('x', type=int)
        y = request.args.get('y', type=int)
        mouse.move(x, y, duration=0.02)
        mouse.click()
        return f'{cmd} {x} {y}'
    
    elif cmd == 'write':
        key = request.args.get('key', type=str)
        keyboard.write(key)
        return f'{cmd} {key}'
    
    return 'Done'


if __name__ == '__main__':
    # Flask 로그 억제 (중요)
    #import logging
    #logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
