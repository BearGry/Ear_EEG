import numpy as np
from devices import EEGNet, SaveModelThread
import time


if __name__ == "__main__":
    import json


    model_type = "EEGNet"
    left_data = np.load('E:/Desktop/Ear_EEG/exp_data/exp_2025_10_16_19_33_42_left.npy')
    right_data = np.load('E:/Desktop/Ear_EEG/exp_data/exp_2025_10_16_19_33_42_right.npy')
    with open("E:/Desktop/Ear_EEG/exp_data/exp_2025_10_16_19_33_42.json", 'r', encoding='utf-8') as load_f:
        info = json.load(load_f)
        model = EEGNet(final_feature_dim=len(info['action_map']))
        save_model_thread = SaveModelThread()
        save_model_thread.train_and_save_model(
            exp_left_data=left_data,
            exp_right_data=right_data,
            exp_info=info,
            model=model,
            model_type=model_type,
            epochs=100
        )
        while True:
            time.sleep(1)
