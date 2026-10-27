import FreeSimpleGUI as sg
import os
import json
import dxcam
import cv2
import numpy as np
import win32clipboard
import win32gui
import threading
from datetime import datetime
import time
import serial
import serial.tools.list_ports

if not os.path.isdir("capture"):
    os.system("mkdir capture")

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

def save_roi_image():
    roi_frame = frame[custom_roi[1]:custom_roi[3], custom_roi[0]:custom_roi[2]]
    now = datetime.now()
    time_stamp = now.strftime('%y%m%d%M%S')
    cv2.imwrite(f'capture/{time_stamp}_capture_{str(custom_roi)[1:-1]}.png', roi_frame)

def save_worker():
    while True:
        if rec_on:
            save_roi_image()
        time.sleep(1)

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

def send_keys(keys):
    # print(keys)
    key_ary = keys.split()
    key_str = ''
    for key in key_ary:
        if ',' in key:
            x, y = key.split(',')
            x = int(int(x)/screen_width*1000)
            y = int(int(y)/screen_height*1000)
            key_str += f'{x},{y} '
        elif key == '@클릭':
            x, y = slots[name]['value'][1] + slots[name]['roi'][0], slots[name]['value'][2] + slots[name]['roi'][1]
            x = int(x/screen_width*1000)
            y = int(y/screen_height*1000)
            key_str += f'{x},{y} '
        else:
            key_str += f'{key} '
    command = key_str.strip()
    ser.write(command.encode())

slots = {}

cam = dxcam.create(output_color='BGR')
cam.start(target_fps=30)
frame = cam.get_latest_frame()

screen_height, screen_width = frame.shape[:2]
custom_roi = [0,0,screen_width, screen_height]

preview_width = 300
preview_height = int(screen_height / (screen_width / preview_width))
preview_show = True
print(f'Preview size : {preview_width}x{preview_height}')

ser = connect_serial()

tool_show = False

timer_keys = ['key', 'cooltime']
image_keys = ['key', 'cooltime', 'target', 'roi', 'threshold']

box_color = (180, 255, 0)

rec_on = False
threading.Thread(target=save_worker, daemon=True).start()

sg.theme('Default1')

layout = [
    [sg.Frame('Preview', [
        [sg.pin(sg.Image('', background_color='gray', size=(preview_width,preview_height), key='img_preview', visible=preview_show))],
        [sg.Sizer(preview_width+10,0)]], key='frame_preview')
    ],
    [sg.Frame('Tool', [
        [sg.pin(sg.Image('', background_color='gray', size=(preview_width,preview_height), key='img_roi', visible=tool_show))],
        [sg.Sizer(preview_width+10,0)],
        [sg.pin(sg.Text('', key='mouse_pos', visible=False))],
        [
            sg.pin(sg.Text('', key='custom_roi', visible=False), expand_x=True),
            sg.pin(sg.Button('Set ROI', key='roi_set', visible=False), expand_x=True),
            sg.pin(sg.Button('Copy text', key='roi_clipboard', visible=False), expand_x=True)
        ],
        [
            sg.pin(sg.Button('Save ROI image', key='save_roi', visible=False, expand_x=True), expand_x=True),
            sg.pin(sg.Button('Record ROI image', key='record_roi', visible=False, expand_x=True), expand_x=True)
        ]
    ], key='frame_tool')],
    [sg.Button('Load', expand_x=True), sg.Button('Pause', expand_x=True)],
    [sg.Column([], key="container", vertical_scroll_only=True)]
]


window = sg.Window('Automation', layout, finalize=True)
window.bind('<Control-KeyPress-1>', 'CTRL-1')
window.bind('<Control-KeyPress-2>', 'CTRL-2')
window.bind('<Control-KeyPress-3>', 'CTRL-3')
window['frame_preview'].bind('<Button-1>', ':CLICK')
window['frame_tool'].bind('<Button-1>', ':CLICK')

while True:
    frame = cam.get_latest_frame()
    event, value = window.read(timeout=0)
    mouse_x, mouse_y = win32gui.GetCursorPos()

    if event == sg.WINDOW_CLOSED:
        break

    elif event == 'record_roi':
        rec_on = not rec_on
    
    elif event == 'Pause':
        print(slots)

    elif event == 'Load':
        filename = sg.popup_get_file('Select file', default_path=os.getcwd(), no_window=True, multiple_files=True)
        for file in filename:
            name = file.split('/')[-1].split('.')[0]
            with open(file, 'r', encoding='utf-8') as f:
                slots[name] = json.load(f)
                slots[name]['cooling'] = False
                slots[name]['value'] = None
                #check
                if slots[name]['type'] == 'timer':
                    print(f'timer : {name}')
                    new_row = [[sg.Frame(name, [[sg.Checkbox('Run', key=f'run_{name}')]], size=(preview_width+5, 50))]]
                    window.extend_layout(window["container"], new_row)
                
                elif slots[name]['type'] == 'image':
                    print(f'image: {name}')
                    target_ary = slots[name]['target']
                    image_ary = []
                    image_thumbnail_ary = []
                    for target in target_ary:
                        img = load_img(f'resources/{target}')
                        image_ary.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
                    slots[name]['target'] = image_ary
                    new_row = [[sg.Frame(name, [[sg.Checkbox('Run', key=f'run_{name}')], [sg.Image(size=(preview_width, 80), background_color='gray', key=f'img_{name}')]], size=(preview_width+5, 130))]]
                    window.extend_layout(window["container"], new_row)
            
    elif event == 'frame_preview:CLICK':
        preview_show = not preview_show
        window['img_preview'].update(visible=preview_show)
        
    elif event == 'frame_tool:CLICK':
        tool_show = not tool_show
        window['img_roi'].update(visible=tool_show)
        window['mouse_pos'].update(visible=tool_show)
        window['custom_roi'].update(visible=tool_show)
        window['save_roi'].update(visible=tool_show)
        window['record_roi'].update(visible=tool_show)
        window['roi_clipboard'].update(visible=tool_show)
        window['roi_set'].update(visible=tool_show)
        
    elif event == 'CTRL-1':
        if mouse_x < custom_roi[2] and mouse_y < custom_roi[3]:
            custom_roi[0], custom_roi[1] = mouse_x, mouse_y
        else:
            print('P1 has to smaller then P2')
        
    elif event == 'CTRL-2':
        if mouse_x > custom_roi[0] and mouse_y > custom_roi[1]:
            custom_roi[2], custom_roi[3] = mouse_x, mouse_y
        else:
            print('P2 has to bigger then P1')
    
    elif event == 'CTRL-3':
        custom_roi = [0,0,screen_width, screen_height]
        
    elif event == 'save_roi':
        save_roi_image()
    
    elif event == 'roi_clipboard':
        text = str(custom_roi)[1:-1]
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
        
    elif event == 'roi_set':
        value = sg.popup_get_text('Type your roi : x1, y1, x2, y2', 'App', keep_on_top=True)
        if value != None:
            try:
                custom_roi = list(map(int, value.strip().split(',')))
            except:
                print('Error')
                custom_roi = [0,0,screen_width, screen_height]
                
    if preview_show:
        preview = cv2.resize(frame, dsize=(preview_width,preview_height), interpolation=cv2.INTER_LINEAR)
        if ser == None:
            cv2.putText(preview, 'Serial not connected', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
        window['img_preview'].update(data=cv2.imencode('.ppm', preview)[1].tobytes())
    
    if tool_show:
        roi_frame = frame[custom_roi[1]:custom_roi[3], custom_roi[0]:custom_roi[2]]
        roi_preview = resize_keep_ratio_pad(roi_frame, preview_width, preview_height)
        if rec_on:
            cv2.putText(roi_preview, 'REC', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
        window['mouse_pos'].update(f'Mouse position: {mouse_x}, {mouse_y}')
        window['custom_roi'].update(f'ROI: [{custom_roi[0]},{custom_roi[1]},{custom_roi[2]},{custom_roi[3]}]')
        window['img_roi'].update(data=cv2.imencode('.ppm', roi_preview)[1].tobytes())
        
    #Timer
    for name in slots:
        if slots[name]['type'] == 'timer':
            if window[f'run_{name}'].get():
                if not slots[name]['cooling']:
                    cooling_on(name)
                    cmd = slots[name]['key']
                    #Send
                    send_keys(cmd)
    
    #Image
        if slots[name]['type'] == 'image':
            thres = slots[name]['threshold']
            roi = slots[name]['roi']
            background = frame[roi[1]:roi[3], roi[0]:roi[2]].copy()
            result = find_img(background, slots[name]['target'])
            cx = result[0] + result[2]//2
            cy = result[1] + result[3]//2
            result_bool = result[4] >= thres
            slots[name]['value'] = (result_bool, cx, cy)
            cv2.rectangle(background, (result[0], result[1]), (result[0]+result[2], result[1]+result[3]), box_color, 10)
            cv2.line(background, (0, cy), (background.shape[1], cy), box_color, 5)
            cv2.line(background, (cx, 0), (cx, background.shape[0]), box_color, 5)
            preview = resize_keep_ratio_pad(background, preview_width-10, 80)
            cv2.putText(preview, f'{result[4]}/{thres}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
            window[f'img_{name}'].update(data=cv2.imencode('.ppm', preview)[1].tobytes())
            if window[f'run_{name}'].get():
                if result[4] >= thres:
                    if not slots[name]['cooling']:
                        cooling_on(name)
                        cmd = slots[name]['key']
                        send_keys(cmd)


window.close()
