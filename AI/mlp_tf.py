import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

df = pd.read_csv('boston.csv', index_col=[0])

X = df.drop('MEDV', axis=1)
Y = df['MEDV']

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)

model = tf.keras.models.Sequential()
model.add(tf.keras.layers.Dense(24, activation='relu', input_shape=[12]))
model.add(tf.keras.layers.Dense(12, activation='relu'))
model.add(tf.keras.layers.Dense(6, activation='relu'))
model.add(tf.keras.layers.Dense(1))
optimizer = tf.keras.optimizers.Adam(0.001)
model.compile(loss='mse', optimizer=optimizer, metrics=['mae', 'mse'])
model.summary()

hist = model.fit(X_train.to_numpy(), Y_train.to_numpy(), epochs=100, validation_split=0.3)

pred = model.predict(X_test.to_numpy())
r2 = r2_score(Y_test, pred)
print(f'R2 score: {r2:.4f}')