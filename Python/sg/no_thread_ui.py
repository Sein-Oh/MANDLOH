import FreeSimpleGUI as sg
import os
import json
import dxcam
import cv2
import numpy as np
import time
import win32gui

slots = {}

cam = dxcam.create(output_color='BGR')
cam.start(target_fps=30)
frame = cam.get_latest_frame()

screen_height, screen_width = frame.shape[:2]

preview_width = 320
preview_height = int(screen_height / (screen_width / preview_width))
preview_show = True
print(f'Preview size : {preview_width}x{preview_height}')

tool_show = False

sg.theme('Default1')


layout = [
    [sg.Frame('Preview', [
        [sg.pin(sg.Image('', background_color='gray', size=(preview_width,preview_height), key='img_preview', visible=preview_show))],
        [sg.Sizer(330,0)]], key='frame_preview')
    ],
    [sg.Frame('Tool', [
        [sg.pin(sg.Image('', background_color='gray', size=(preview_width,preview_height), key='img_tool', visible=tool_show))],
        [sg.Sizer(330,0)],
        [sg.pin(sg.Text('', key='mouse_pos', visible=False))]
    ], key='frame_tool')],
    [sg.Button('Load', expand_x=True), sg.Button('Pause', expand_x=True)],
]


window = sg.Window('Automation', layout, finalize=True)
window.bind('<Control-KeyPress-1>', 'CTRL-1')
window.bind('<Control-KeyPress-2>', 'CTRL-2')
window['frame_preview'].bind('<Button-1>', ':CLICK')
window['frame_tool'].bind('<Button-1>', ':CLICK')

while True:
    frame = cam.get_latest_frame()
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
        window['img_tool'].update(visible=tool_show)
        window['mouse_pos'].update(visible=tool_show)
    
    if preview_show:
        preview = cv2.resize(frame, dsize=(preview_width,preview_height), interpolation=cv2.INTER_LINEAR)
        window['img_preview'].update(data=cv2.imencode('.ppm', preview)[1].tobytes())
    
    if tool_show:
        mouse_x, mouse_y = win32gui.GetCursorPos()
        window['mouse_pos'].update(f'Mouse position : {mouse_x}, {mouse_y}')
    
    
window.close()
