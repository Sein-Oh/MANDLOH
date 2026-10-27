import cv2, os, glob
import numpy as np
image_dir = 'images'
image_path = glob.glob(image_dir + '/*.png')

result_dir = 'results'
if os.path.exists(result_dir) == False:
    os.mkdir(data_dir)
save_path = [w.replace(image_dir, result_dir) for w in image_path]

isDown, show = False, False
x0, y0, x1, y1 = None, None, None, None
def onmouse(event, x, y, flags, params):
    global isDown, show, x0, y0, x1, y1
    if event == cv2.EVENT_LBUTTONDOWN:
        x0, y0 = int(x), int(y)
        isDown, show = True, False
    elif event == cv2.EVENT_MOUSEMOVE:
        if isDown:
            x1, y1 = int(x), int(y)
            show = True
    elif event == cv2.EVENT_LBUTTONUP:
        isDown, show = False, True

def remove_bkg(img, roi):
    mask = np.zeros(img.shape[:2],np.uint8)
    bgdModel = np.zeros((1,65),np.float64)
    fgdModel = np.zeros((1,65),np.float64)
    cv2.grabCut(img, mask, roi, bgdModel, fgdModel,5,cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask==2)|(mask==0),0,1).astype('uint8')
    img_cut = img*mask2[:,:,np.newaxis]
    return img_cut

img_num = 0
while True:
    cv2.namedWindow(image_path[img_num])
    cv2.setMouseCallback(image_path[img_num], onmouse)
    img_ori = cv2.imread(image_path[img_num])
    img = img_ori.copy()
    if show:
        cv2.rectangle(img, (x0, y0), (x1, y1), (0,255,0), 2)
    cv2.imshow(image_path[img_num], img)
    key = cv2.waitKeyEx(33)
    if key == ord('q'):
        cv2.destroyAllWindows()
        break
    elif key == 32: #space
        roi = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        print(roi)
        output = remove_bkg(img_ori, roi)
        cv2.imshow('output', output)
        cv2.imwrite(save_path[img_num], output)
    elif key == 2424832: #Left arrow
        if img_num > 0:
            img_num -= 1
            cv2.destroyAllWindows()
    elif key == 2555904: #Right arrow
        if img_num < len(image_path)-1:
            img_num += 1
            cv2.destroyAllWindows()
