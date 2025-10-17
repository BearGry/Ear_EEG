import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
from scipy import signal

from collections import deque


class EEGPlotter:
    def __init__(self, plot_widget:pg.PlotWidget, 
                 packets_per_second=10, samples_per_packet=50, window_duration=5,
                 lowcut=0.01, highcut=100.0, side="left"):
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

        # 带通滤波器参数
        self.signal_processor = EEGSignalProcessor(lowcut=lowcut, highcut=highcut, sample_rate=self.sample_rate)
        
        self.init_plot(side)

    def init_plot(self, side):
        """初始化绘图窗口"""
        # 清空并设置绘图窗口
        self.plot_widget.clear()
        self.plot_widget.setLabel('left', '电压', 'µV')
        self.plot_widget.setLabel('bottom', '时间', 's')
        self.plot_widget.setTitle(f'单导联脑电图信号 - 固定时间窗口模式 - {side}')
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
        if self.refresh_line is not None:
            self.plot_widget.removeItem(self.refresh_line)  
        self.refresh_line = self.plot_widget.addLine(
            x=0, 
            pen=pg.mkPen(color='white', width=2)
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
        
        # 带通滤波，并转换为numpy数组
        new_data = self.signal_processor.process_realtime(voltage_data)

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
        # if len(self.data_buffer) > 0:
        #     data_range = np.max(self.data_buffer) - np.min(self.data_buffer)
        #     if data_range > 10:
        #         margin = data_range * 0.1
        #         self.plot_widget.setYRange(
        #             np.min(self.data_buffer) - margin, 
        #             np.max(self.data_buffer) + margin
        #         )



class EEGSignalProcessor:
    def __init__(self, lowcut, highcut, sample_rate):
        self.sample_rate = sample_rate

        """设置带通滤波器"""
        # 带通滤波器 (0.01-100Hz) - 同时处理直流漂移和高频噪声
        self.lowcut = lowcut
        self.highcut = highcut

        nyquist = 0.5 * self.sample_rate
        
        # 标准化截止频率
        low_normalized = lowcut / nyquist
        high_normalized = highcut / nyquist
        
        # 4阶巴特沃斯带通滤波器
        # 这个滤波器会自动：
        # 1. 去除直流分量（相当于高通）
        # 2. 去除高频噪声（相当于低通）
        # 3. 保持滤波器状态确保数据连续性
        self.band_b, self.band_a = signal.butter(4, [low_normalized, high_normalized], btype='band')
        self.filter_zi = None
        
    def process_realtime(self, data_chunk:list) -> np.ndarray:
        """
        优化的实时处理：单个带通滤波器解决所有问题
        """
        # 转换为numpy数组            
        data = np.array(data_chunk, dtype=np.float64)
        
        # 使用滤波器状态确保数据连续性
        if self.filter_zi is None:
            # 第一次处理：初始化滤波器状态
            filtered, self.filter_zi = signal.lfilter(
                self.band_b, self.band_a, data, zi=signal.lfilter_zi(self.band_b, self.band_a))
        else:
            # 后续处理：使用之前的状态，确保连续滤波
            filtered, self.filter_zi = signal.lfilter(
                self.band_b, self.band_a, data, zi=self.filter_zi)
        
        return filtered
    
    def reset(self):
        """重置滤波器状态（例如设备重连时）"""
        self.filter_zi = None
        print("滤波器状态已重置")