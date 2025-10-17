import json
import os
import sys

import numpy as np
from scipy.signal import butter, filtfilt
from scipy.fft import fft

import torch
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split


def band_pass_filter(data, axis, fs, fmin, fmax):
    b, a = butter(2, [fmin * 2 / fs, fmax * 2 / fs], 'bandpass')
    filtered_data = filtfilt(b, a, data, axis=axis)
    return filtered_data

def get_abs_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception as e:
        # print(f'get_abs_path error: {e}')
        base_path = os.path.abspath(".")
    return os.path.abspath(os.path.join(base_path, relative_path)).replace("\\", "/")

def write_dict_to_json(data, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def extract_fft_feature(data):
    assert len(data.shape) == 3
    n_times = data.shape[2]
    fft_features = fft(data, axis=2)  # 对第三维时间轴进行FFT变换
    fft_magnitude = np.abs(fft_features)  # 取模得到幅度谱
    return fft_magnitude[:, :, :n_times // 2 + 1]  # 只取前半部分频谱

# 加载和预处理数据
def load_and_preprocess_eegnet_data(left_data, right_data, info):
    """
    加载数据并提取特征
    exp_info={
                "action_map": self.ACTION,
                "left_data_length": len(exp_left_data),
                "right_data_length": len(exp_right_data),
                "left_sample_rate": 500,
                "right_sample_rate": 500,
                "mark": self.mark,
            }
    """
    markers = info['mark']
    sample_rate1 = info['left_sample_rate']
    sample_rate2 = info['right_sample_rate']
    twindow_sample = int(2 * sample_rate1)
    twindow_sample2 = int(2 * sample_rate2)

    left_data = band_pass_filter(left_data, axis=0, fs=sample_rate1, fmin=0.05,
                                 fmax=100)
    right_data = band_pass_filter(right_data, axis=0, fs=sample_rate2, fmin=0.05,
                                 fmax=100)

    X, X1, y = [], [], []
    for m in markers:
        start = m[0]
        start1 = m[1]
        end = start + twindow_sample
        end1 = start1 + twindow_sample2
        X.append(left_data[start:end])
        X1.append(right_data[start1:end1])
        y.append(m[2])


    X = np.stack(X)
    X1 = np.stack(X1)
    y = np.array(y).astype(np.int64)
    X = X.reshape(-1, twindow_sample, 1)  # (实验轮数*分类数, 1000(窗口大小), 1(通道))
    X1 = X1.reshape(-1, twindow_sample, 1)  # (实验轮数*分类数, 1000(窗口大小), 1(通道))
    X_train = np.concatenate((X1, X1),axis=2) # (实验轮数*分类数, 1000(窗口大小), 2(通道))

    x_subject = np.rollaxis(X_train, 2, 1).astype(np.float32) # as.(40, 2, 1000)

    x_train, x_val, y_train, y_val = train_test_split(x_subject, y, test_size=0.2, random_state=42)
    train_dataset = TensorDataset(torch.tensor(x_train), torch.tensor(y_train))
    val_dataset = TensorDataset(torch.tensor(x_val), torch.tensor(y_val))

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    return train_loader, val_loader