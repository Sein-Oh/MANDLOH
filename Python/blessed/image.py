from blessed import Terminal
import dxcam
from term_image.image import AutoImage
from PIL import Image
import numpy as np
import cv2


cam = dxcam.create(output_color="BGR")
cam.start(target_fps=30)

def PIL2OpenCV(pil_image):
    numpy_image= np.array(pil_image)
    opencv_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
    return opencv_image

def OpenCV2PIL(opencv_image):
    color_coverted = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(color_coverted)
    return pil_image

term = Terminal()
print(term.clear())

with term.cbreak(), term.hidden_cursor():
  while True:
    with term.location(0,0):
       frame = cam.get_latest_frame()
       frame = cv2.resize(frame, dsize=(1280,720), interpolation=cv2.INTER_AREA)
       frame_pil = OpenCV2PIL(frame)
       img = AutoImage(frame_pil)
       print(img)
