import os, glob
import cv2
import numpy as np

image_dir = 'images'
image_path = glob.glob(image_dir + '/*.png')

result_dir = 'results'
if os.path.exists(result_dir) == False:
    os.mkdir(data_dir)
save_path = [w.replace(image_dir, result_dir) for w in image_path]

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
    img = cv2.imread(image_path[img_num])
    roi = cv2.selectROI('image', img)
    output = remove_bkg(img, roi)
    
    gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
    ret, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
    cv2.imshow('image', binary)
    cv2.imwrite(save_path[img_num], output)
    
    key = cv2.waitKeyEx(0)
    if key == ord('q'):
        cv2.destroyAllWindows()
        break
    elif key == 2424832: #Left arrow
        if img_num > 0:
            img_num -= 1
    elif key == 2555904: #Right arrow
        if img_num < len(image_path)-1:
            img_num += 1
