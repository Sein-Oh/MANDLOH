import base64
import numpy as np
import cv2

#To avoid error message
import warnings
warnings.simplefilter("ignore", DeprecationWarning)

img = cv2.imdecode(np.fromstring(base64.b64decode(uri.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)
cv2.imshow('img', img)