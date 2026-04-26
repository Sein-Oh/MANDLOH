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

exit_flag = False
capture_method = 'SCREEN CAPTURE'
input_method = 'NOT CONNECTED'
recording = False

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


def draw_header():
    header_height = 6
    inner_width = term.width - 1
    title = ' INFORMATION '
    if mouse_y > -1 and inp.name == 'MOUSE_LEFT' and mouse_y <= header_height:
        print(term.clear())
    with term.location(0, 0):
        print(term.white('─' * 2) + term.black_on_white(title) + term.white('─' * (inner_width - len(title) - 2)))
        print(f"{' CAPTURE'.ljust(13)}: {capture_method}".ljust(term.width))
        print(f"{' SCREEN SIZE'.ljust(13)}: {screen_width} x {screen_height}".ljust(term.width))
        print(f"{' ROI'.ljust(13)}: {roi[0]},{roi[1]},{roi[2]},{roi[3]}".ljust(term.width))
        print(f"{' INPUT'.ljust(13)}: {input_method}".ljust(term.width))
        print(f"{' RECORDING'.ljust(13)}: {'YES' if recording else 'NO'}".ljust(term.width))
        print(term.white('─' * inner_width))


def draw_slots(row):
    inner_width = term.width - 1
    title = ' SLOTS '
    with term.location(0, row):
        # Top
        print(term.white('─' * 2) + term.black_on_white(title) + term.white('─' * (inner_width - len(title) - 2)))

        for idx, key in enumerate(slots):
            # 클릭 토글
            if mouse_y > -1 and inp.name == 'MOUSE_LEFT':
                if mouse_y == idx + row + 1:
                    slots[key]['run'] = not slots[key]['run']

            is_on = slots[key]['run']
            color = term.green2 if is_on else term.gray
            if slots[key]['type'] == 'timer':
                line = f' [T] {key}'
            elif slots[key]['type'] == 'img':
                value = slots[key]['value'][0]
                x = slots[key]['value'][1] + roi[0]
                y = slots[key]['value'][2] + roi[1]
                line = f' [I] {key} [{value}-{x},{y}]'
            print(f'{color(line)}'.ljust(term.width))
        # Bottom
        print(term.white('─' * inner_width))


def footer_draw():
    global exit_flag
    footer_height = 3
    row = term.height - footer_height
    with term.location(0, row):
        print(term.white('─' * term.width))
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        print(term.bold(term.green(time_str.ljust(term.width))))
    if mouse_y > -1 and inp.name == 'MOUSE_LEFT' and mouse_y > row and mouse_y <= row + footer_height:
        exit_flag = True



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

num_timers = len([key for key in slots if slots[key]['type'] == 'timer'])
num_imgs = len([key for key in slots if slots[key]['type'] == 'img'])

cam = dxcam.create(output_color='BGR')
cam.start(target_fps=5)
frame = cam.get_latest_frame()

screen_height, screen_width = frame.shape[:2]
roi = [0,0,screen_width,screen_height]

ser = connect_serial()
if ser:
    input_method = f'SERIAL ({ser.port})'

print(term.clear)

try:
    with term.cbreak(), term.hidden_cursor(), term.fullscreen(), term.mouse_enabled():
        while True:
            # Capture
            frame = cam.get_latest_frame()

            frame = frame[roi[1]:roi[3], roi[0]:roi[2]]
            inp = term.inkey(timeout=0)

            # Mouse
            mouse_y = inp.mouse_xy[1] if inp.mouse_xy else -1

            # Keyboard
            pressed_key = inp.name if inp.is_sequence else inp

            if pressed_key == 'KEY_F1':
                # Capture
                filename = f'capture/{time.strftime("%Y%m%d_%H%M%S")}_capture.png'
                cv2.imwrite(filename, frame)
                time.sleep(0.1)
                os.startfile(os.path.abspath(filename))

            elif pressed_key == 'KEY_F2':
                # Show slot
                filename = f'capture/{time.strftime("%Y%m%d_%H%M%S")}_slot.png'
                stacked_img = np.vstack([info for info in img_slot_info])
                cv2.imwrite(filename, stacked_img)
                time.sleep(0.1)
                os.startfile(os.path.abspath(filename))      

            elif pressed_key == 'KEY_F3':
                recording = not recording

            elif pressed_key == 'KEY_ESCAPE' or exit_flag:
                break
            
            elif pressed_key == 'KEY_F5':
                mx, my = mouse.get_position()
                if mx < roi[2] and my < roi[3]: 
                    roi[0], roi[1] = mx, my
            
            elif pressed_key == 'KEY_F6':
                mx, my = mouse.get_position()
                if mx > roi[0] and my > roi[1]:
                    roi[2], roi[3] = mx, my

            elif pressed_key == 'KEY_F7':
                roi = [0,0,screen_width,screen_height]



            # Timer
            for name in slots:
                if slots[name]['type'] == 'timer':
                    if slots[name]['run']:
                        if not slots[name]['cooling']:
                            cooling_on(name)
                            cmd = slots[name]['key']
                            #Send
                            # add_message(f'{name} ACTIVATED')


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
                    cv2.putText(frame_copy, f"{name} {slots[name]['value'][:3]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 1, cv2.LINE_AA)
                    
                    # ROI box
                    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255,0,0), 3)

                    # Result box
                    cv2.rectangle(frame_copy, (result[0]+x1, result[1]+y1), (result[0]+x1+result[2], result[1]+y1+result[3]), (0,255,0), 3)
                    img_slot_info.append(frame_copy)


            draw_header()
            draw_slots(7)
            footer_draw()

            time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    print(term.normal_cursor(), end='')
    print(term.exit_fullscreen(), end='')