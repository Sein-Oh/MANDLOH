import numpy as np
import cv2
import dxcam
import cvui
import json
import os

print('Slot loading...', end="")
slots = {}
json_ary = [j for j in os.listdir('resources') if '.json' in j]
for filename in json_ary:
    name = filename.split('.')[0]
    with open(f'resources/{filename}', "r", encoding="utf-8") as f:
        slots[name] = json.load(f)
print(f' Found {len(json_ary)} files.')

print('Prepare capture...', end="")
fps = 30
cam = dxcam.create(output_color='BGR')
cam.start(target_fps=fps)

capture = cam.get_latest_frame()
capture_height, capture_width, _ = capture.shape
print(f' Start capture with {capture_width}x{capture_height} @{fps}FPS')

preview_width = 320
preview_height = int(capture_height / (capture_width / preview_width))
print(f'Preview size : {preview_width}x{preview_height}')

#Checkbox values
cb_values = [[False] for i in range(len(slots.keys()))]

window_name = 'CVUI'
cvui.init(window_name)
frame = np.zeros((600, 330, 3), np.uint8)

while True:
    frame[:] = (49, 52, 49)
    capture = cam.get_latest_frame()
    preview = cv2.resize(capture, dsize=(preview_width, preview_height), interpolation=cv2.INTER_LINEAR)
    cvui.image(frame, 5, 5, preview)
    
    for i, key in enumerate(slots.keys()):
        cvui.checkbox(frame, 5, preview_height + 15 + i * 25, key, cb_values[i])
    
    for i, key in enumerate(slots.keys()):
        if cb_values[i][0] == True:
            print(key)
    
    cvui.imshow(window_name, frame)
    if cv2.waitKey(1) == ord('q'):
        break
