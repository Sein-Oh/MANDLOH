from pycaret.classification import *
import cv2
import numpy as np
import pandas as pd
import glob
import os

net = cv2.dnn.readNetFromONNX("mobilenetv2_feature.onnx")
clf = load_model("catdog_model.pkl")

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

def predict(img_path):
    blob = extract_features(img_path)
    blob = blob.reshape(1, -1)
    df = pd.DataFrame(blob)
    pred = predict_model(clf, df)
    label = pred["prediction_label"][0]
    score = pred["prediction_score"][0]
    print(f"{label} : {score} {img_path}")


image_paths = glob.glob("./train/*.jpg")
for path in image_paths[:40]:
    predict(path)

"""
features = []
file_names = []

for path in image_paths[:40]:
    feat = extract_features(path)
    features.append(feat)
    
X = pd.DataFrame(features)
print(X)
pred_df = predict_model(clf, data=X)
print(pred_df)
"""
