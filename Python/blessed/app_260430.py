from blessed import Terminal
import time
import threading
import os
import cv2
import numpy as np

import dxcam
import mouse
import serial
import serial.tools.list_ports

term = Terminal()

if not os.path.isdir('capture'):
    os.system('mkdir capture')


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


def cooling_off(key):
    slots[key]['cooling'] = False


def cooling_on(key):
    slots[key]['cooling'] = True
    th = threading.Timer(float(slots[key]['cooltime']), cooling_off, [key])
    th.daemon = True
    th.start()


def find_ports():
    ports = serial.tools.list_ports.comports()
    port_list = []
    for port in ports:
        port_list.append(port.device)
    return port_list


def connect_serial():
    ports = find_ports()
    if len(ports) < 1:
        print('No serial ports found.')
        return None
    else:
        for port in ports:
            try:
                ser = serial.Serial(port, baudrate=9600, timeout=1)
                ser.write(b'check')
                if ser.readline() == b'ok\r\n':
                    print(f'Connected on {port}.')
                    return ser
            except:
                print('Failed to connect serial.')
                return None


def prompt(legend, msg):
        print(term.clear)
        text = ''
        while True:
            title(0, f' {legend} ')
            draw(1, f'{term.yellow(msg)} {text}'.ljust(term.width))
            draw(3, f'Submit(Enter) / Cancel(Esc)'.center(term.width))
            draw(4, term.orange('=' * term.width))

            inp = term.inkey()
            pressed_key = '' if inp.is_sequence and 'MOUSE' in inp.name else (inp.name if inp.is_sequence else inp)
            if 'KEY' in pressed_key:
                if pressed_key == 'KEY_BACKSPACE':
                    text = text[:-1]
                elif pressed_key == 'KEY_ENTER':
                    print(term.clear)
                    return text
                elif pressed_key == 'KEY_ESCAPE':
                    print(term.clear)
                    return ''
            else:                
                text = text + pressed_key
            

def exit_terminal():
        print(term.clear)
        print(term.normal_cursor(), end='')
        print(term.exit_fullscreen(), end='')
        os._exit(0)

def event_handler(event):
    if event == 'clear':
        print(term.clear)
    elif event == 'exit':
        exit_terminal()
    elif event == 'set_roi':
        value = prompt('Set ROI', 'Enter roi value (x1,y1,x2,y2) :')
        set_roi(value)
    elif event == 'toggle_recording':
        toggle_recording()

    for key in slots.keys():
        if event == key:
            slots[key]['run'] = not slots[key]['run']


def draw(row, text, mouse_y=-1, event=None):
    with term.location(0, row):
        print(text)
    if mouse_y == row:
        event_handler(event)


def title(row, label, mouse_y=-1, event=None):
    inner_width = term.width - 1
    with term.location(0, row):
        print(term.orange('─' * 1) + term.orange(label) + term.orange('─' * (inner_width - len(label) - 1)))
    if mouse_y == row:
        event_handler(event)


def set_roi(value):
    global roi
    try:
        data = [int(x) for x in value.split(',')]
        if not (data[0] < data[2] and data[1] < data[3]):
            return
    except:
        return
    if len(data) != 4:
        return
    else:
        roi = data


def toggle_recording():
    global recording
    recording = not recording

################## START ##################
capture_method = 'NOT_SELECTED'
input_method = 'NOT_SELECTED'
recording = False

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


fps = 10
cam = dxcam.create(output_color='BGR')
cam.start(target_fps=fps)
frame = cam.get_latest_frame()
screen_height, screen_width = frame.shape[:2]
roi = [0,0,screen_width,screen_height]

capture_method = f'SCREEN CAPTURE {screen_width}x{screen_height} {fps}FPS'


try:
    with term.cbreak(), term.hidden_cursor(), term.fullscreen(), term.mouse_enabled():
        while True:
            # Capture
            frame = cam.get_latest_frame()
            frame = frame[roi[1]:roi[3], roi[0]:roi[2]]


            inp = term.inkey(timeout=0)
            # Mouse
            mouse_x, mouse_y = inp.mouse_xy if (inp.mouse_xy and inp.name == 'MOUSE_LEFT') else (-1, -1)
            # Keyboard
            pressed_key = inp.name if inp.is_sequence else inp
            
            # INFORMATION
            draw(0, f'{time.strftime('%Y-%m-%d %H:%M:%S')} '.rjust(term.width), mouse_y, 'clear')
            draw(1, '', mouse_y, 'clear')
            title(2, ' INFORMATION |', mouse_y)
            draw(3, f'  {term.blue("CAPTURE".center(12))}  {capture_method}')
            draw(4, f'  {term.blue("ROI".center(12))}  {roi[0]},{roi[1]},{roi[2]},{roi[3]}', mouse_y, 'set_roi')
            draw(5, f'  {term.blue("INPUT".center(12))}  {input_method}')
            draw(6, f'  {term.blue("RECORDING".center(12))}  {term.green("ON") if recording else term.red("OFF")}'.ljust(term.width), mouse_y, 'toggle_recording')
            draw(7, term.orange('─' * term.width))
            
            # SLOTS
            title(9, ' SLOTS |', mouse_y)
            for idx, key in enumerate(slots.keys()):
                i = idx + 10
                if slots[key]['type'] == 'timer':
                    draw(i, f'  {term.green(key.center(12)) if slots[key]["run"] else term.red(key.center(12))}  {term.blue("COOLTIME") if slots[key]["cooling"] else term.green("STANDBY")}'.ljust(term.width), mouse_y, key)
                elif slots[key]['type'] == 'img':
                    value = slots[key]["value"]
                    draw(i, f'  {term.green(key.center(12)) if slots[key]["run"] else term.red(key.center(12))}  SCORE:{value[0]}  X:{value[1]}  Y:{value[2]}'.ljust(term.width), mouse_y, key)
                if idx == len(slots)-1:
                    draw(i+1, term.orange('─' * term.width))
            

            # Footer
            draw(term.height-3, term.white('─' * term.width))
            draw(term.height-2, term.yellow('EXIT'.center(term.width)), mouse_y, 'exit')
            if pressed_key == 'KEY_F1':
                # Capture
                filename = f'capture/{time.strftime("%Y%m%d_%H%M%S")}_capture.png'
                cv2.imwrite(filename, frame)
                time.sleep(0.1)
                os.startfile(os.path.abspath(filename))
            

            # Timer
            for name in slots:
                if slots[name]['type'] == 'timer':
                    if slots[name]['run']:
                        if not slots[name]['cooling']:
                            cooling_on(name)
                            cmd = slots[name]['key']            

            # Image
            img_slot_info = []
            for idx, name in enumerate(slots):
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
                    slots[name]['value'] = (result[4], cx, cy, result_bool)
                    if slots[name]['run']:
                        if result[4] >= thres:
                            if not slots[name]['cooling']:
                                cooling_on(name)
                                cmd = slots[name]['key']

                    # Draw slot info
                    frame_copy = frame.copy()
                    # Draw Label
                    cv2.putText(frame_copy, f"{name} {slots[name]['value'][:3]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2, cv2.LINE_AA)
                    
                    # ROI box
                    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255,0,0), 3)

                    # Result box
                    cv2.rectangle(frame_copy, (result[0]+x1, result[1]+y1), (result[0]+x1+result[2], result[1]+y1+result[3]), (0,255,0), 5)
                    
                    frame_copy =cv2.resize(frame_copy, dsize=(0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
                    img_slot_info.append(frame_copy)

            time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    exit_terminal()
