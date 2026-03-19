import numpy as np
import cv2
import dxcam
import cvui

cam = dxcam.create(output_color='BGR')
cam.start(target_fps=30)

capture = cam.get_latest_frame()
capture_height, capture_width, _ = capture.shape

preview_width = 320
preview_height = int(capture_height / (capture_width / preview_width))
print(f'Preview size : {preview_width}x{preview_height}')

window_name = 'CVUI'
cvui.init(window_name)
frame = np.zeros((600, 330, 3), np.uint8)

files = ['file1', 'file2', 'file3']
states = [[False] for i in range(len(files))]

while True:
    frame[:] = (49, 52, 49)
    capture = cam.get_latest_frame()
    preview = cv2.resize(capture, dsize=(preview_width, preview_height), interpolation=cv2.INTER_LINEAR)
    cvui.image(frame, 5, 5, preview)
    
    for i, file in enumerate(files):
        cvui.checkbox(frame, 5, 240 + i * 20, files[i], states[i])
    
    cvui.imshow(window_name, frame)
    if cv2.waitKey(1) == ord('q'):
        break
