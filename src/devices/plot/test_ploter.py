import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
from PySide6.QtCore import QObject, Signal, QTimer, QTime
import numpy as np

from eegPloter import EEGPlotter

# 模拟信号类
class Signals(QObject):
    plot_data = Signal(list)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建绘图部件
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        
        # 创建EEG绘图器
        self.eeg_plotter = EEGPlotter(self.plot_widget)
        
        # 创建模拟信号
        self.data_signal = Signals()
        self.data_signal.plot_data.connect(self.eeg_plotter.update_plot)
        
        # 设置窗口
        self.setWindowTitle('单导联脑电图显示')
        self.setGeometry(100, 100, 800, 600)
        
        # 启动模拟数据发送
        self.start_simulation()
    
    def start_simulation(self):
        """模拟设备发送数据"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.generate_simulated_data)
        self.timer.start(100)  # 每100ms发送一次 (10次/秒)
    
    def generate_simulated_data(self):
        """生成模拟的EEG数据"""
        # 模拟脑电信号: 基础信号 + 噪声
        import random
        t = QTime.currentTime().msec() / 1000.0
        base_signal = 50 * np.sin(2 * np.pi * 10 * t)  # 10Hz alpha波
        noise = [random.gauss(0, 10) for _ in range(50)]  # 高斯噪声
        simulated_data = [base_signal + n for n in noise]
        
        # 发送信号
        self.data_signal.plot_data.emit(simulated_data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


