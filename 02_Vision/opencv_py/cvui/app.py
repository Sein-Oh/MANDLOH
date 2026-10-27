import numpy as np
import cv2
import dxcam
import cvui
import json
import os
import threading
import ctypes
import sys
import time

print('App start.')
print('Made by Mandloh(2026.03.20)')
print('')
setting_checker = True

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

def resize_to_50x50(img):
    target_size = 50
    h, w = img.shape[:2]
    if w > h:
        scale = target_size / w
    else:
        scale = target_size / h
    new_w = int(round(w*scale))
    new_h = int(round(h*scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    result = np.zeros((target_size, target_size, 3), np.uint8)
    x_offset = (target_size - new_w) //2
    y_offset = (target_size - new_h) //2
    result[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return result

def cooling_off(key):
    slots[key]['cooling'] = False

def cooling_on(key):
    slots[key]['cooling'] = True
    th = threading.Timer(float(slots[key]['cooltime']), cooling_off, [key])
    th.daemon = True
    th.start()

def key_checker(d, keys):
    return all(key in d for key in keys)

print('Slot loading...', end='')
slots = {}
json_ary = [j for j in os.listdir('resources') if '.json' in j]
for filename in json_ary:
    name = filename.split('.')[0]
    with open(f'resources/{filename}', 'r', encoding='utf-8') as f:
        slots[name] = json.load(f)
print(f' Found {len(json_ary)} files.')

print('Check timer slot key values.')
timer_num = 0
timer_keys = ['key', 'cooltime']
for key in slots:
    if slots[key]['type'] == 'timer':
        print(f' - {key}...', end='')
        if key_checker(slots[key], timer_keys):
            slots[key]['cooling'] = False
            print('OK.')
            timer_num += 1
        else:
            print('\033[31mFailed.\033[0m')
            setting_checker = False

print('Check image slot key values.')
image_num = 0
image_keys = ['key', 'cooltime', 'target', 'roi', 'threshold']
for key in slots:
    if slots[key]['type'] == 'image':
        print(f' - {key}...', end='')
        if key_checker(slots[key], image_keys):
            slots[key]['cooling'] = False
            print('OK.')
            image_num += 1
        else:
            print('\033[31mFailed.\033[0m')
            setting_checker = False
print(f'{timer_num} Timer, {image_num} Image slots are loaded.')
print('')

print('Check image target files.')
for key in slots:
    if slots[key]['type'] == 'image':
        target_ary = slots[key]['target']
        image_ary = []
        image_thumbnail_ary = []
        for target in target_ary:
            try:
                img = load_img(f'resources/{target}')
                img_thumbnail = resize_to_50x50(img)
                image_thumbnail_ary.append(img_thumbnail)
                image_ary.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
                print(f' - {target} OK.')
            except:
                print(f' - \033[31m{target} load failed.\033[0m')
                setting_checker = False
        slots[key]['targets'] = image_ary
        slots[key]['result_thumbnail'] = image_thumbnail_ary


print('')
print('Prepare capture...', end='')
f = 10
cam = dxcam.create(output_color='BGR')
cam.start(target_fps=f)

capture = cam.get_latest_frame()
capture_height, capture_width = capture.shape[:2]
print(f' Start capture with {capture_width}x{capture_height} @{f}FPS')

preview_width = 320
preview_height = int(capture_height / (capture_width / preview_width))
print(f'Preview size : {preview_width}x{preview_height}')

#Checkbox values
cb_values = [[False] for i in range(len(slots.keys()))]


#Calc frame size
frame_height = preview_height + (timer_num * 25) + (image_num * 55) + 35
window_name = 'CVUI'
cvui.init(window_name)
frame = np.zeros((frame_height, 330, 3), np.uint8)


if setting_checker:
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

while True:
    start_time = time.time()
    frame[:] = (49, 52, 49)
    capture = cam.get_latest_frame()
    preview = cv2.resize(capture, dsize=(preview_width, preview_height), interpolation=cv2.INTER_LINEAR)
    cvui.image(frame, 5, 5, preview)
    
    if cvui.button(frame, 10, preview_height + 5, 'Uncheck'):
        cb_values = [[False] for i in range(len(slots.keys()))]
    
    #Timer
    timer_height = 0
    j = 0
    for i, key in enumerate(slots.keys()):
        if slots[key]['type'] == 'timer':
            timer_height += 25
            cooltime = slots[key]['cooltime']
            cmd = slots[key]['key']
            #Action
            text_color = 0xffffff #White
            if cb_values[i][0]:
                if not slots[key]['cooling']:
                    cooling_on(key)
                    print(f'{key}')
                    #Add serial command
                else:
                    text_color = 0x0000ff #Blue
            cvui.checkbox(frame, 10, preview_height + 40 + j * 25, f'{key.ljust(8)} {cmd}', cb_values[i], text_color)
            j += 1
    
    #Image
    j = 0
    for i, key in enumerate(slots.keys()):
        if slots[key]['type'] == 'image':
            cooltime = slots[key]['cooltime']
            cmd = slots[key]['key']
            thres = slots[key]['threshold']
            #Calculation
            roi = slots[key]['roi']
            background = capture[roi[1]:roi[3], roi[0]:roi[2]]
            result = find_img(background, slots[key]['targets'])
            max_val = result[4]
            slots[key]['result_thumbnail'][0] = resize_to_50x50(capture[result[1]:result[1]+result[3], result[0]:result[0]+result[2]])
            #Action
            text_color = 0xffffff #White
            if cb_values[i][0]:
                if max_val > thres:
                    if not slots[key]['cooling']:
                        cooling_on(key)
                        print(f'{key}')
                        #Add serial command
                    else:
                        text_color = 0x0000ff #Blue
            cvui.checkbox(frame, 10, preview_height + 55 + timer_height + j * 55, f'{key.ljust(8)} [{max_val}>{thres}] {key}', cb_values[i], text_color)
            cvui.image(frame, 275, preview_height + 40 + timer_height + j * 55, slots[key]['result_thumbnail'][0])
            j += 1
    
                
    
    fps = 1 / (time.time() - start_time)
    cvui.text(frame, 5, 5, f'{fps:.2f} FPS', 0.4, 0x00FF00)
    cvui.imshow(window_name, frame)
    cv2.waitKey(1)
    
    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
        break
    
    
