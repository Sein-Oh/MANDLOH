import os, glob
import numpy as np
from keras.preprocessing.image import load_img, img_to_array
from sklearn.model_selection import train_test_split
from u_net import get_unet_128

input_size, model = get_unet_128()

img_path = 'input/train'
img_ext = '.jpg'
img_form = img_path + '/{}' + img_ext

lbl_path = 'input/label'
lbl_ext = '.png'
lbl_form = lbl_path + '/{}' + lbl_ext

img_names = glob.glob(img_path + '/*' + img_ext)
img_names = [names.replace('\\', '/') for names in img_names]
img_names = [names.split('/')[-1].split('.')[0] for names in img_names]
print('Found {} images.'.format(len(img_names)))

def train_gen():
    while True:
        train, valid = train_test_split(img_names, test_size=0.10, random_state=42)
        x_batch = []
        y_batch = []
        for name in train:
            im_path = img_form.format(name)
            lb_path = lbl_form.format(name)
            
            img = load_img(im_path, color_mode='rgb', target_size=(input_size, input_size))
            img = img_to_array(img)
            
            lbl = load_img(lbl_path, color_mode='grayscale', target_size=(input_size, input_size))
            lbl = img_to_array(label)
            
            x_batch.append(img)
            y_batch.append(label)
        x_batch = np.array(x_batch, np.float32) / 255
        y_batch = np.array(y_batch, np.float32) / 255
        yield x_batch, y_batch

def valid_gen():
    while True:
        train, valid = train_test_split(img_names, test_size=0.10, random_state=42)
        x_batch = []
        y_batch = []
        for name in valid:
            im_path = img_form.format(name)
            lb_path = lbl_form.format(name)
            
            img = load_img(im_path, color_mode='rgb', target_size=(input_size, input_size))
            img = img_to_array(img)
            
            lbl = load_img(lbl_path, color_mode='grayscale', target_size=(input_size, input_size))
            lbl = img_to_array(label)
            
            x_batch.append(img)
            y_batch.append(label)
        x_batch = np.array(x_batch, np.float32) / 255
        y_batch = np.array(y_batch, np.float32) / 255
        yield x_batch, y_batch

model.fit_generator(
    train_gen(),
    steps_per_epoch=15,
    epochs=20
)

model.save('my_model.h5')