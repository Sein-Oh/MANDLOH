import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.adam import Adam
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

df = pd.read_csv('boston.csv', index_col=[0])

X = df.drop('MEDV', axis=1)
Y = df['MEDV']

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)

data_X = torch.from_numpy(X_train.to_numpy()).float()
data_y = torch.from_numpy(Y_train.to_numpy()).float().reshape(-1, 1)

model = nn.Sequential(
    nn.Linear(12, 24),
    nn.ReLU(),
    nn.Linear(24, 12),
    nn.ReLU(),
    nn.Linear(12, 6),
    nn.ReLU(),
    nn.Linear(6, 1)
)

optimizer = Adam(model.parameters(), lr=0.001)
epochs = 100
batch_size = 32

for epoch in range(epochs):
    for i in range(len(data_X)//batch_size):
        start = i * batch_size
        end = start + batch_size

        x = torch.FloatTensor(data_X[start:end])
        y = torch.FloatTensor(data_y[start:end])

        optimizer.zero_grad()
        preds = model(x)
        loss = nn.MSELoss()(preds, y)
        loss.backward()
        optimizer.step()

    print(f'Epoch {epoch}, Loss: {loss.item():.4f}')

pred = model(torch.from_numpy(X_test.to_numpy()).float())
r2 = r2_score(Y_test.to_numpy(), pred.detach())
print(f'R2 score: {r2:.4f}')