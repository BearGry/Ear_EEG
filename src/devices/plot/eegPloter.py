import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
from collections import deque


class EEGPlotter:
    def __init__(self, plot_widget:pg.PlotWidget, packets_per_second=10, samples_per_packet=50, window_duration=5):
        self.plot_widget = plot_widget
        self.data_buffer = None
        self.time_buffer = None
        self.curve = None
        self.refresh_line = None
        
        # 设备参数
        self.packets_per_second = packets_per_second
        self.samples_per_packet = samples_per_packet
        self.window_duration = window_duration  # 5秒窗口
        self.sample_rate = self.packets_per_second * self.samples_per_packet  # 500Hz

        # 计算缓冲区大小
        self.buffer_size = self.sample_rate * self.window_duration  # 2500个样本
        
        # 跟踪当前时间位置和刷新状态
        self.refresh_line_pos = 0
        
        self.init_plot()
    
    def init_plot(self):
        """初始化绘图窗口"""
        # 清空并设置绘图窗口
        self.plot_widget.clear()
        self.plot_widget.setLabel('left', '电压', 'µV')
        self.plot_widget.setLabel('bottom', '时间', 's')
        self.plot_widget.setTitle('单导联脑电图信号 - 固定时间窗口模式')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置颜色和背景
        self.plot_widget.setBackground('w')
        
        # 初始化数据缓冲区 - 全零
        self.data_buffer = np.zeros(self.buffer_size)
        
        # 初始化时间轴 (从0到5秒固定)
        self.time_buffer = np.linspace(0, self.window_duration, self.buffer_size)
        
        # 创建曲线对象
        self.curve = self.plot_widget.plot(
            self.time_buffer, 
            self.data_buffer,
            pen=pg.mkPen(color='b', width=1)
        )
        
        # 创建刷新线
        self.refresh_line = self.plot_widget.addLine(
            x=0, 
            pen=pg.mkPen(color='r', width=2, style=QtCore.Qt.DashLine)
        )
        
        # 设置坐标轴范围
        self.plot_widget.setXRange(0, self.window_duration)
        self.plot_widget.setYRange(-200, 200)  # 根据实际信号幅度调整
        
        print(f"EEG绘图初始化完成: 采样率{self.sample_rate}Hz, 缓冲区{self.buffer_size}样本")
    
    def update_plot(self, voltage_data):
        """
        处理plot_data信号的槽函数
        voltage_data: 包含50个电压值的列表
        """
        if len(voltage_data) != self.samples_per_packet:
            print(f"警告: 期望{self.samples_per_packet}个数据点, 收到{len(voltage_data)}个")
            return
        
        # 转换为numpy数组
        new_data = np.array(voltage_data)
        
        # 计算新数据在缓冲区中的位置
        start_idx = self.refresh_line_pos
        end_idx = start_idx + self.samples_per_packet
        
        self.data_buffer[start_idx:end_idx] = new_data

        # 更新刷新线位置
        self.refresh_line_pos = end_idx % self.buffer_size

        self.refresh_line.setValue(self.refresh_line_pos / self.sample_rate)

        # 更新曲线数据
        self.curve.setData(self.time_buffer, self.data_buffer)
        
        # 自动调整Y轴范围以适应数据
        if len(self.data_buffer) > 0:
            data_range = np.max(self.data_buffer) - np.min(self.data_buffer)
            if data_range > 0:
                margin = data_range * 0.1
                self.plot_widget.setYRange(
                    np.min(self.data_buffer) - margin, 
                    np.max(self.data_buffer) + margin
                )