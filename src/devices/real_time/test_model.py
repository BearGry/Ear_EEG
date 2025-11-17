from PySide6.QtCore import QThread, Signal
import torch
import numpy as np


class RealTimeTestModelThread(QThread):
    '''
    实时测试，给出每次测试的结果即可
    '''
    real_time_result_signal = Signal(torch.Tensor)    

    def __init__(self, model=None, weight_path="../../../exp_models/EEGNet/weight.pth"):
        super().__init__()
        self.model = model
        self.weight_path = weight_path
        try:
            self.model.load_state_dict(torch.load(self.weight_path))
            print("Successfully loaded model weights from", self.weight_path)
        except FileNotFoundError:
            raise FileNotFoundError("No existing model weights file found. Please train the model first.")
        except Exception as e:
            raise RuntimeError(f"Error loading model weights: {e}")


    def run(self, left_test_data=None, right_test_data=None):
        # 这里可以添加实际的测试代码
        left_test_data = np.array(left_test_data).reshape(1, 1, -1)
        right_test_data = np.array(right_test_data).reshape(1, 1, -1)

        # 如果只用一只耳朵的数据测试模型，记得修改这一行
        input_data = np.concatenate((left_test_data, right_test_data), axis=1)
        input_tensor = torch.tensor(input_data, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            # print(f"Raw model output: {output}")
            output = torch.softmax(output, dim=1).squeeze(0)
            self.real_time_result_signal.emit(output)
