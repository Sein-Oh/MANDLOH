import glob
import cv2
import numpy as np
import pandas as pd
from pycaret.classification import *

net = cv2.dnn.readNetFromONNX("mobilenetv2_feature.onnx")


def extract_features(img_path):    
    img = cv2.imread(img_path)
    blob = cv2.dnn.blobFromImage(img, scalefactor=1/255.0, size=(224,224), mean=(0,0,0), swapRB=True, crop=False)
    net.setInput(blob)
    features = net.forward()
    features = features.mean(axis=(2, 3))
    #shape (1, 1280)
    features = features.flatten()
    #shape (1280,)
    return features

img_dir = "test"
X, y = [], []

files = glob.glob("./test/*.jpg")
for filename in files:
    if "cat" in filename:
        label = "cat"
    elif "dog" in filename:
        label = "dog"
    else:
        print("Error")
    
    feat = extract_features(filename)
    X.append(feat)
    y.append(label)
    
X = np.array(X)
y = np.array(y)
print(f"Feature shape : {X.shape}, Labels : {len(y)}")

df = pd.DataFrame(X)
df["label"] = y

print(df)

clf_setup = setup(
    data = df,
    target = "label",
    normalize=True,
    session_id=42
)

best_model = compare_models()
final_model = finalize_model(best_model)
save_model(final_model, "catdog_model.pkl")
print("완료")
