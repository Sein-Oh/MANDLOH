import FreeSimpleGUI as sg
import os
import json
import dxcam
import cv2
import numpy as np
import time
import win32gui

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

tool_show = False

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
        [sg.pin(sg.Text('', key='custom_roi', visible=False))],
        [sg.pin(sg.Button('Save ROI image', key='save_roi', visible=False, expand_x=True))]
    ], key='frame_tool')],
    [sg.Button('Load', expand_x=True), sg.Button('Pause', expand_x=True)],
]


window = sg.Window('Automation', layout, finalize=True)
window.bind('<Control-KeyPress-1>', 'CTRL-1')
window.bind('<Control-KeyPress-2>', 'CTRL-2')
window.bind('<Control-KeyPress-3>', 'CTRL-3')
window['frame_preview'].bind('<Button-1>', ':CLICK')
window['frame_tool'].bind('<Button-1>', ':CLICK')

while True:
    frame = cam.get_latest_frame()
    mouse_x, mouse_y = win32gui.GetCursorPos()
    event, value = window.read(timeout=0)
    if event != '__TIMEOUT__':
        print(event)
    if event == sg.WINDOW_CLOSED:
        break
    
    elif event == 'Load':
        filename = sg.popup_get_file('Select file', default_path=os.getcwd(), no_window=True, multiple_files=True)
        try:
            for file in filename:
                name = file.split('/')[-1].split('.')[0]
                with open(file, 'r', encoding='utf-8') as f:
                    slots[name] = json.load(f)
            print(slots)
        except:
            print('File load failed')
            
    elif event == 'frame_preview:CLICK':
        preview_show = not preview_show
        window['img_preview'].update(visible=preview_show)
        
    elif event == 'frame_tool:CLICK':
        tool_show = not tool_show
        window['img_roi'].update(visible=tool_show)
        window['mouse_pos'].update(visible=tool_show)
        window['custom_roi'].update(visible=tool_show)
        window['save_roi'].update(visible=tool_show)
        
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
        roi_frame = frame[custom_roi[1]:custom_roi[3], custom_roi[0]:custom_roi[2]]
        cv2.imwrite('capture.png', roi_frame)
    
    
    if preview_show:
        preview = cv2.resize(frame, dsize=(preview_width,preview_height), interpolation=cv2.INTER_LINEAR)
        window['img_preview'].update(data=cv2.imencode('.ppm', preview)[1].tobytes())
    
    if tool_show:
        roi_frame = frame[custom_roi[1]:custom_roi[3], custom_roi[0]:custom_roi[2]]
        roi_preview = resize_keep_ratio_pad(roi_frame, preview_width, preview_height)
        window['mouse_pos'].update(f'Mouse position: {mouse_x}, {mouse_y}')
        window['custom_roi'].update(f'ROI: [{custom_roi[0]},{custom_roi[1]},{custom_roi[2]},{custom_roi[3]}]')
        window['img_roi'].update(data=cv2.imencode('.ppm', roi_preview)[1].tobytes())
        
    
window.close()
