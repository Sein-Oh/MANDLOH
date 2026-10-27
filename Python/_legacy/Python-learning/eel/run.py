import eel, io, base64
import numpy as np
import matplotlib.pyplot as plt

eel.init('web')
@eel.expose
def send_image(msg):
    print('run')
    img = io.BytesIO(np.fromstring(base64.b64decode(msg.split(',')[1]), np.uint8))
    img = plt.imread(img, format='JPG')
    plt.imsave('save.jpg', img)

eel.start('rtc.html')
