import numpy as np
from devices import EEGNet, SaveModelThread
import time


if __name__ == "__main__":
    import json


    model_type = "EEGNet"
    left_data = np.load('./exp_data/exp_2025_11_17_15_55_03_left.npy')
    right_data = np.load('./exp_data/exp_2025_11_17_15_55_03_right.npy')
    with open("./exp_data/exp_2025_11_17_15_55_03.json", 'r', encoding='utf-8') as load_f:
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
