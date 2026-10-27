import FreeSimpleGUI as sg
import dxcam
import cv2
import numpy as np
import time
import mouse

cam = dxcam.create(output_color='BGR')
cam.start(target_fps=30)
frame = cam.get_latest_frame()

screen_width = frame.shape[1]
screen_height = frame.shape[0]

preview_width = int(screen_width / 4)
preview_height = int(screen_height / 4)

roi_preview_show = False

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

def update_frame():
    while True:
        frame = cam.get_latest_frame()
        preview = cv2.resize(frame, dsize=(preview_width, preview_height), interpolation=cv2.INTER_AREA)
        mouse_pos = mouse.get_position()
        # cv2.putText(preview, f'({mouse_x},{mouse_y})', (preview_width-130, preview_height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        data = {'preview':preview, 'mouse_pos':mouse_pos}
        window.write_event_value('-preview-', data)
        if roi_preview_show:
            try:
                roi = window['roi_input'].get()
                rois = roi.split(',')
                rois = list(map(str.strip, rois))
                x, y, w, h = map(int, rois)
                roi_frame = frame[y:y+h, x:x+w]
                roi_preview = resize_keep_ratio_pad(roi_frame, preview_width, preview_height)
                window.write_event_value('-roi_preview-', roi_preview)
            except:
                pass


layout = [
    [sg.Frame('캡쳐', [
        [
            sg.Image(key='preview', size=(preview_width, preview_height))
        ],
        [
            sg.Text('캡쳐영역'),
            sg.Radio('보기', group_id=1, key='roi_show', enable_events=True),
            sg.Radio('닫기', group_id=1, default=True, key='roi_hide', enable_events=True),
            sg.Input(f'0,0,{screen_width},{screen_height}', key='roi_input', disabled=True,  size=(18,None)),
            sg.Text("마우스:(0,0)", key='mouse_pos')
        ],
        [
            sg.pin(sg.Image(key='roi_preview', size=(preview_height, preview_height), visible=False))
        ]
    ])],
    [sg.Frame('슬롯', [
        [
            sg.Button('이미지')
        ]
    ])]
]

window = sg.Window('Window Title', layout, finalize=True)
window.start_thread(update_frame)

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break

    elif event == '-preview-':
        window['preview'].update(data=cv2.imencode('.ppm', values[event]['preview'])[1].tobytes())
        window['mouse_pos'].update(f'마우스 위치:({values[event]['mouse_pos'][0]},{values[event]['mouse_pos'][1]})')

    elif event == '-roi_preview-':
        window['roi_preview'].update(data=cv2.imencode('.ppm', values[event])[1].tobytes())

    elif event == 'roi_show':
        window['roi_preview'].update(visible=True)
        window['roi_input'].update(disabled=False)
        roi_preview_show = True
    
    elif event == 'roi_hide':
        window['roi_preview'].update(visible=False)
        window['roi_input'].update(disabled=True)
        roi_preview_show = False

    else:
        print(event)


window.close()