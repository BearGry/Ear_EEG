# -*- coding: utf-8 -*-
"""
LSL (Lab Streaming Layer) 流管理模块
用于将左右耳EEG数据发送成两个独立的LSL流
"""

from pylsl import StreamInfo, StreamOutlet
import numpy as np
from threading import Lock


class LSLStreamer:
    """管理左右耳的两个独立LSL流"""
    
    def __init__(self, sample_rate=500):
        """
        初始化LSL流管理器
        
        Args:
            sample_rate: 采样率，默认500Hz
        """
        self.sample_rate = sample_rate
        self.left_outlet = None
        self.right_outlet = None
        self.lock = Lock()
        
    def create_streams(self):
        """
        创建左右耳的两个LSL流
        注意：左右耳使用不同的频率需要在硬件或应用层处理
        """
        try:
            # 创建左耳LSL流信息
            left_info = StreamInfo(
                name='Ear_EEG_Left',
                type='EEG',
                channel_count=1,  # 单通道
                nominal_srate=self.sample_rate,
                channel_format='float32',
                source_id='ear_eeg_left'
            )
            
            # 设置左耳通道描述
            left_desc = left_info.desc()
            left_channels = left_desc.append_child("channels")
            left_channel = left_channels.append_child("channel")
            left_channel.append_child_value("label", "Left_EEG")
            left_channel.append_child_value("unit", "microvolts")
            left_channel.append_child_value("type", "EEG")
            
            # 设置左耳采样率信息
            left_desc.append_child_value("manufacturer", "Naoyun")
            left_desc.append_child_value("device", "Ear_EEG_Left")
            
            # 创建左耳数据输出口
            self.left_outlet = StreamOutlet(left_info)
            print("✓ 左耳LSL流已创建: Ear_EEG_Left @ 500Hz")
            
            # 创建右耳LSL流信息
            right_info = StreamInfo(
                name='Ear_EEG_Right',
                type='EEG',
                channel_count=1,  # 单通道
                nominal_srate=self.sample_rate,
                channel_format='float32',
                source_id='ear_eeg_right'
            )
            
            # 设置右耳通道描述
            right_desc = right_info.desc()
            right_channels = right_desc.append_child("channels")
            right_channel = right_channels.append_child("channel")
            right_channel.append_child_value("label", "Right_EEG")
            right_channel.append_child_value("unit", "microvolts")
            right_channel.append_child_value("type", "EEG")
            
            # 设置右耳采样率信息
            right_desc.append_child_value("manufacturer", "Naoyun")
            right_desc.append_child_value("device", "Ear_EEG_Right")
            
            # 创建右耳数据输出口
            self.right_outlet = StreamOutlet(right_info)
            print("✓ 右耳LSL流已创建: Ear_EEG_Right @ 500Hz")
            
            return True
        except Exception as e:
            print(f"✗ 创建LSL流失败: {str(e)}")
            return False
    
    def push_left_sample(self, sample):
        """
        推送左耳单个样本到LSL流
        
        Args:
            sample: 单个数据点 (float)
        """
        if self.left_outlet is None:
            return
        
        try:
            with self.lock:
                # LSL需要列表格式 [channel1, channel2, ...]
                self.left_outlet.push_sample([float(sample)])
        except Exception as e:
            print(f"推送左耳样本失败: {str(e)}")
    
    def push_right_sample(self, sample):
        """
        推送右耳单个样本到LSL流
        
        Args:
            sample: 单个数据点 (float)
        """
        if self.right_outlet is None:
            return
        
        try:
            with self.lock:
                self.right_outlet.push_sample([float(sample)])
        except Exception as e:
            print(f"推送右耳样本失败: {str(e)}")
    
    def push_left_chunk(self, samples):
        """
        推送左耳多个样本到LSL流 (批量操作更高效)
        
        Args:
            samples: 数据列表或numpy数组 (1D)
        """
        if self.left_outlet is None:
            return
        
        try:
            with self.lock:
                if isinstance(samples, np.ndarray):
                    samples = samples.tolist()
                elif not isinstance(samples, list):
                    samples = list(samples)
                
                # 将每个样本转换为[sample]格式后推送
                for sample in samples:
                    self.left_outlet.push_sample([float(sample)])
        except Exception as e:
            print(f"推送左耳数据块失败: {str(e)}")
    
    def push_right_chunk(self, samples):
        """
        推送右耳多个样本到LSL流 (批量操作更高效)
        
        Args:
            samples: 数据列表或numpy数组 (1D)
        """
        if self.right_outlet is None:
            return
        
        try:
            with self.lock:
                if isinstance(samples, np.ndarray):
                    samples = samples.tolist()
                elif not isinstance(samples, list):
                    samples = list(samples)
                
                # 将每个样本转换为[sample]格式后推送
                for sample in samples:
                    self.right_outlet.push_sample([float(sample)])
        except Exception as e:
            print(f"推送右耳数据块失败: {str(e)}")
    
    def close_streams(self):
        """关闭所有LSL流"""
        try:
            self.left_outlet = None
            self.right_outlet = None
            print("✓ LSL流已关闭")
        except Exception as e:
            print(f"关闭LSL流失败: {str(e)}")
    
    def is_connected(self):
        """检查是否已连接"""
        return self.left_outlet is not None and self.right_outlet is not None


# 使用示例
if __name__ == "__main__":
    import time
    
    # 初始化LSL流
    lsl = LSLStreamer(sample_rate=500)
    lsl.create_streams()
    
    # 模拟数据发送
    try:
        for i in range(int(1e10)):
            left_sample = np.sin(2 * np.pi * i / 100) * 100
            right_sample = np.cos(2 * np.pi * i / 100) * 100
            
            lsl.push_left_sample(left_sample)
            lsl.push_right_sample(right_sample)
            
            time.sleep(0.002)  # 500Hz采样率对应2ms
    except KeyboardInterrupt:
        print("\n停止发送")
    finally:
        lsl.close_streams()
