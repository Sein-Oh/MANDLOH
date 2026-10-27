from flask import Flask, Response, request
from flask_cors import CORS
import cv2
import dxcam
import datetime
from blessed import Terminal
import os
import keyboard
import mouse

# --- Blessed 터미널 초기화 ---
term = Terminal()
app = Flask(__name__)
CORS(app)

host = '127.0.0.1'
port = 8000

def log_msg(category, message, color):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    # 카테고리별로 색상을 다르게 적용
    cat_text = color(f"{category:10}")
    print(f"{term.white_bold(f'[{timestamp}]')} {cat_text} {term.white('|')} {message}")

# MANDLOH ASCII 배너 (해커 테마)
BANNER = f"""
{term.bright_cyan(term.bold(r"""
  ███╗   ███╗ █████╗ ███╗   ██╗██████╗ ██╗      ██████╗ ██╗  ██╗
  ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██║     ██╔═══██╗██║  ██║
  ██╔████╔██║███████║██╔██╗ ██║██║  ██║██║     ██║   ██║███████║
  ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██║     ██║   ██║██╔══██║
  ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝███████╗╚██████╔╝██║  ██║
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝"""))}
          {term.on_color(4)(term.white_bold("  [ SYSTEM: MANDLOH STREAMING SERVER ]  "))}
"""

print(term.clear) # 실행 시 화면 초기화
print(BANNER)
log_msg("SYSTEM", "Server start.", term.bright_magenta)

# 화면캡처 생성
try:
    cam = dxcam.create(output_color="BGR")
    cam.start(target_fps=30)
    frame = cam.get_latest_frame()
    height, width, _ = frame.shape
    log_msg("SYSTEM", f"Capture size: {term.underline(f'{width}x{height}')}", term.bright_magenta)
except Exception as e:
    log_msg("SYSTEM", f"Capture failed: {e}", term.bright_magenta)
    log_msg("SYSTEM", f"Server terminated", term.bright_magenta)
    os._exit(0)

log_msg("SYSTEM", f"Stream URL : http://{host}:{port}", term.bright_magenta)
log_msg("SYSTEM", f"Input URL : http://{host}:{port}/input", term.bright_magenta)


def gen():
    log_msg("SYSTEM", "Client Connection Detected", term.bright_magenta)
    try:
        while True:
            frame = cam.get_latest_frame()
            if frame is None: continue
            
            encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
            f = image_buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + f"{len(f)}".encode() + b'\r\n'
                   b'\r\n' + f + b'\r\n')
    except Exception:
        log_msg("SYSTEM", "Client Session Ended", term.bright_red)

@app.route('/')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


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
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    try:
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print(f"\n{term.bright_red('Stopping server...')}")
