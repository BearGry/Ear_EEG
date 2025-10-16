from PySide6.QtCore import QThread, Signal
import time
import random


class ExperimentThread(QThread):
    update_label_signal = Signal(str, int)
    action_signal = Signal(str)
    exp_finished = Signal()

    def __init__(self, epochs=10, actions=None):
        super().__init__()
        self.epochs = epochs
        self.actions = actions if actions else ["闭眼", "咬牙", "左看", "右看"]

    def run(self):
        print(f"开始实验，共 {self.epochs} 轮")
        time.sleep(8)
        for epoch in range(1, self.epochs + 1):
            print(f"第 {epoch} 轮实验")
            actions = self.actions.copy()
            random.shuffle(actions)
            for i in range(len(actions)):
                # 准备阶段
                self.update_label_signal.emit(f"准备: {actions[i]}", 0)
                time.sleep(2)
                # 执行阶段
                self.update_label_signal.emit(f"执行: {actions[i]}", 1)
                self.action_signal.emit(actions[i])
                time.sleep(2)
                # 休息阶段
                self.update_label_signal.emit("休息", 2)
                time.sleep(2)

        print("实验结束")
        self.exp_finished.emit()