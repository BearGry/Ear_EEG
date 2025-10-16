import numpy as np
import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
import torch.optim as optim
import os
from scipy.signal import butter, filtfilt



class EEGNet(nn.Module):
    def __init__(self, final_feature_dim=4):
        super(EEGNet, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=2, out_channels=32, kernel_size=16, padding=3)
        self.pool = nn.MaxPool1d(kernel_size=4)
        self.conv2 = nn.Conv1d(in_channels=32, out_channels=64, kernel_size=16, padding=3)
        self.dropout = nn.Dropout(p=0.5)  # Dropout层用于防止过拟合

        with torch.no_grad():
            test_input = torch.zeros(1, 2, 2*500)
            test_output = self.pool(torch.relu(self.conv2(self.pool(torch.relu(self.conv1(test_input))))))
            fc1_input_size = test_output.view(1, -1).shape[1]

        self.fc1 = nn.Linear(fc1_input_size, 64)

        self.classifier = nn.Linear(64, final_feature_dim)

    def forward(self, x):
        batch_size, channels, time_points = x.size()

        channel_x = x[:, :, :]
        print(channel_x.size())
        channel_x = self.pool(torch.relu(self.conv1(channel_x)))
        channel_x = self.pool(torch.relu(self.conv2(channel_x)))
        channel_x = channel_x.view(batch_size, -1)
        channel_x = torch.relu(self.fc1(channel_x))
        channel_x = self.dropout(channel_x)

        output = self.classifier(channel_x)
        return output





