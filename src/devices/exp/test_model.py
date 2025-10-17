from PySide6.QtCore import QThread, Signal
import torch
import numpy as np


class TestModelThread(QThread):
    model_result_signal = Signal(list)    

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
        self.test_count = 0
        self.right_count = 0

    
    def accurate_rate(self):
        if self.test_count == 0:
            return 0.0
        return self.right_count / self.test_count


    def run(self, left_test_data=None, right_test_data=None, label=None):
        # 模拟测试过程
        print(f"第{self.test_count}次测试模型...")
        # 这里可以添加实际的测试代码
        left_test_data = np.array(left_test_data).reshape(1, 1, -1)
        right_test_data = np.array(right_test_data).reshape(1, 1, -1)
        input_data = np.concatenate((right_test_data, right_test_data), axis=1)
        input_tensor = torch.tensor(input_data, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            print(f"Raw model output: {output}")
            output = torch.softmax(output, dim=1).squeeze(0)
            self.model_result_signal.emit(output.numpy().tolist())
            predicted = torch.argmax(output).item()
            print(f"模型预测结果: {predicted}, 实际标签: {label}")
            self.test_count += 1
            if predicted == label:
                self.right_count += 1