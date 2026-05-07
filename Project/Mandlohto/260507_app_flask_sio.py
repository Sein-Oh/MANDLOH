from flask import Flask, render_template
from flask_socketio import SocketIO
import os
import threading
import time
from typing import List

import cv2
import numpy as np

import mouse
import dxcam
import serial
import serial.tools.list_ports


app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

host = '127.0.0.1'
port = '10025'


def find_ports():
    return [port.device for port in serial.tools.list_ports.comports()]


def connect_serial():
    ports = find_ports()
    if not ports:
        print('No serial ports found.')
        return None
    for port in ports:
        try:
            print(f'Connect {port}...', end=' ')
            ser = serial.Serial(port, baudrate=9600, timeout=1, write_timeout=1)
            time.sleep(1)
            ser.reset_input_buffer()
            ser.write(b'check\n')
            response = ser.readline()
            if response.strip() == b'ok':
                print(f'Connected on {port}.')
                return ser
            ser.close()
        except Exception as e:
            print(f'Failed: {e}')
    return None


def read_txt(path):
    with open(path, 'r', encoding='UTF-8') as file:
        raw_file = file.readlines()
        file = list(map(lambda s: s.strip(), raw_file))
        file = [f for f in file if f]
        return file


def convert_data(data_path):
    result = {}
    for data in read_txt(data_path):
        title, value = list(map(lambda s: s.strip(), data.split(':')))
        result[title] = value
    return result


def load_img(path):
    img_np = np.fromfile(path, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return img


def find_img(background, targets):
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    best_val = -1
    best_result = (0, 0, 0, 0, 0)
    for target in targets:
        h, w = target.shape
        res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val > best_val:
            x, y = max_loc
            best_val = max_val
            best_result = (x, y, w, h, round(max_val, 2))
    return best_result


def cv_to_bytes(img, quality=50):
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buffer.tobytes()


def resize_keep_ratio_pad(img, target_w, target_h, pad_color=(0, 0, 0)):
    h, w = img.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas


def run_server():
    socketio.run(app, host=host, port=port, debug=True, use_reloader=False)


def open_browser():
    os.system(f'start msedge --app=http://{host}:{port}')


def cooling_off(key):
    slots[key]['cooling'] = False


def cooling_on(key):
    slots[key]['cooling'] = True
    th = threading.Timer(float(slots[key]['cooltime']), cooling_off, [key])
    th.daemon = True
    th.start()

def send_key(cmd):
    ser.write(cmd.encode())


def main_loop():
    while True:
        frame = cam.get_latest_frame()
        frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

        thumbnail = resize_keep_ratio_pad(frame, preview_width, preview_height)
        
        roi_text = f"ROI:{','.join(map(str, roi))}"
        font = cv2.FONT_HERSHEY_PLAIN
        alpha = 0.5
        size, baseline = cv2.getTextSize(roi_text, font, 1, 1)
        overlay = thumbnail.copy()
        x,y,w,h = 5, 15, size[0], size[1]
        cv2.rectangle(overlay, (x,0), (x+w,y+h-5), (0,0,0), -1)
        cv2.addWeighted(overlay, alpha, thumbnail, 1-alpha, 0, thumbnail)
        cv2.putText(thumbnail, roi_text, (x,y), font, 1, (250,255,255), 1, cv2.LINE_AA)

        thumbnail_bytes = cv_to_bytes(thumbnail)
        socketio.emit('thumbnail', thumbnail_bytes)

        # Timer
        for name in slots:
            if slots[name]['type'] == 'timer':
                if slots[name]['run']:
                    if not slots[name]['cooling']:
                        cooling_on(name)
                        cmd = slots[name]['key']
                        send_key(cmd)

        #Image
            if slots[name]['type'] == 'img':
                x1 = int(slots[name]['x1'])
                y1 = int(slots[name]['y1'])
                x2 = int(slots[name]['x2'])
                y2 = int(slots[name]['y2'])
                thres = float(slots[name]['threshold'])
                background = frame[y1:y2, x1:x2].copy()
                result = find_img(background, slots[name]['target'])
                cx = x1 + result[0] + result[2]//2
                cy = y1 + result[1] + result[3]//2
                result_bool = result[4] >= thres
                value = (result[4], cx, cy, result_bool)
                slots[name]['value'] = value
                socketio.emit('update_slot', {'key':name, 'value':value})
                if slots[name]['run']:
                    if result[4] >= thres:
                        if not slots[name]['cooling']:
                            cooling_on(name)
                            cmd = slots[name]['key']
                            send_key(cmd)


        time.sleep(0.01)



@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('클라이언트가 연결되었습니다.')
    threading.Thread(target=main_loop, daemon=True).start()
    

@socketio.on('disconnect')
def handle_disconnect():
    print('클라이언트가 연결을 종료했습니다.')
    os._exit(1)


@socketio.on('message')
def handle_message(data:str):
    print('받은 메시지:', data)
    socketio.emit('message', data)


@socketio.on('get_slot_info')
def handle_get_slot_info():
    slot_info = {}
    for key in slots.keys():
        slot_info[key] = {'type': slots[key]['type'], 'run': slots[key]['run']}
    return slot_info


@socketio.on('set_roi_key')
def handle_set_roi_key(p:str):
    global roi
    mx, my = mouse.get_position()
    if p == 'p1':
        if mx < roi[2] and my < roi[3]: 
            roi[0], roi[1] = mx, my
    elif p == 'p2':
        if mx > roi[0] and my > roi[1]:
            roi[2], roi[3] = mx, my
    elif p == 'clear':
        roi = [0,0,screen_width,screen_height]


@socketio.on('set_roi_value')
def handle_set_roi_value(value:List[int]):
    global roi
    if len(value) != 4:
        print('Set roi error.')
        return
    if value[0] < value[2] and value[1] < value[3] and value[2] <= screen_width and value[3] <= screen_height:
        roi = value
    else:
        print('Set roi error.')


@socketio.on('toggle_run')
def handle_toggle_run(key:str):
    if key in slots:
        slots[key]['run'] = not slots[key]['run']
        print(f"Slot '{key}' run state: {slots[key]['run']}")


print('App start.')

print('Connect serial')
ser = connect_serial()

print('Capture screen')
cam = dxcam.create(output_color='BGR')
cam.start(target_fps=30)
frame = cam.get_latest_frame()

screen_height, screen_width = frame.shape[:2]
roi = [0,0,screen_width,screen_height]

preview_width = 300
preview_height = int(screen_height / (screen_width / preview_width))

slots = {}

txt_ary = [j for j in os.listdir('slots') if '.txt' in j]
for txt in txt_ary:
    name = txt.split('.')[0]
    slots[name] = convert_data(f'slots/{txt}')
    slots[name]['run'] = False
    slots[name]['cooling'] = False
    if slots[name]['type'] == 'img':
        slots[name]['value'] = (0, 0, 0, False)
        img_name_ary = [x.replace(' ', '') for x in slots[name]['img'].split()]
        img_ary = []
        for img_name in img_name_ary:
            img = load_img(f'./images/{img_name}')
            img_ary.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        slots[name]['target'] = img_ary


threading.Timer(0.1, open_browser).start()
socketio.run(app, host=host, port=port, debug=True, use_reloader=False)
