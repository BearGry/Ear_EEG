# LSL 流集成指南

## 概述

该项目已集成 **Lab Streaming Layer (LSL)** 功能，可以将左右耳EEG数据实时发送成两个独立的LSL流。

## 功能特点

- ✅ **两个独立流**：左耳数据和右耳数据分别发送到独立的LSL流
- ✅ **单通道传输**：每个流都是单通道（1通道）的EEG数据
- ✅ **实时推送**：数据接收时实时推送到LSL流
- ✅ **500Hz采样率**：标准采样率，可配置
- ✅ **线程安全**：使用锁机制保证数据推送的线程安全

## 安装依赖

### 1. 安装 pylsl 库

```bash
pip install pylsl
```

或者使用 conda：

```bash
conda install -c conda-forge pylsl
```

## 代码集成

### 1. 导入模块

在 `function.py` 中已经导入了 LSL 模块：

```python
from .devices import LSLStreamer
```

### 2. 初始化 LSL 流

在 `get_message()` 方法中，启动数据接收时会自动创建 LSL 流：

```python
# 初始化LSL流
self.lsl_streamer = LSLStreamer(sample_rate=self.SAMPLE_RATE)
if self.lsl_streamer.create_streams():
    print("LSL流已成功创建")
else:
    print("LSL流创建失败，将继续运行但不会发送LSL数据")
```

### 3. 数据推送

当接收到左右耳数据时，会自动推送到对应的 LSL 流：

```python
# 推送左耳数据到LSL流
if self.lsl_streamer is not None and self.lsl_streamer.is_connected():
    self.lsl_streamer.push_left_chunk(data["samples"])

# 推送右耳数据到LSL流
if self.lsl_streamer is not None and self.lsl_streamer.is_connected():
    self.lsl_streamer.push_right_chunk(data["samples"])
```

### 4. 关闭 LSL 流

在停止数据接收时，会自动关闭 LSL 流：

```python
def stop_get_message(self):
    '''停止接收数据，并关闭LSL流'''
    # 关闭LSL流
    if self.lsl_streamer is not None:
        self.lsl_streamer.close_streams()
        self.lsl_streamer = None
```

## LSL 流信息

### 左耳流 (Ear_EEG_Left)

| 属性 | 值 |
|------|-----|
| 流名称 | Ear_EEG_Left |
| 类型 | EEG |
| 通道数 | 1 |
| 采样率 | 500 Hz |
| 数据格式 | float32 |
| 源ID | ear_eeg_left |
| 通道标签 | Left_EEG |
| 单位 | 微伏(µV) |

### 右耳流 (Ear_EEG_Right)

| 属性 | 值 |
|------|-----|
| 流名称 | Ear_EEG_Right |
| 类型 | EEG |
| 通道数 | 1 |
| 采样率 | 500 Hz |
| 数据格式 | float32 |
| 源ID | ear_eeg_right |
| 通道标签 | Right_EEG |
| 单位 | 微伏(µV) |

## 使用方法

### 在 UI 中添加控制按钮

如果需要在UI中添加 LSL 流的启动/停止控制，可以修改 `main.py`：

```python
# 连接停止接收按钮
widgets.btn_stop_message.clicked.connect(self.func.stop_get_message)
```

### 独立使用 LSL 流

可以直接使用 `LSLStreamer` 类：

```python
from src.devices import LSLStreamer
import numpy as np
import time

# 创建流管理器
lsl = LSLStreamer(sample_rate=500)

# 创建流
lsl.create_streams()

# 发送数据
for i in range(100):
    left_sample = np.sin(2 * np.pi * i / 100) * 100
    right_sample = np.cos(2 * np.pi * i / 100) * 100
    
    lsl.push_left_sample(left_sample)
    lsl.push_right_sample(right_sample)
    
    time.sleep(0.002)  # 500Hz对应2ms

# 关闭流
lsl.close_streams()
```

## 接收 LSL 数据

### 在 Python 中接收

```python
from pylsl import resolve_stream, StreamInlet
import numpy as np

# 查找并连接到左耳流
streams = resolve_stream('name', 'Ear_EEG_Left')
inlet_left = StreamInlet(streams[0])

# 查找并连接到右耳流
streams = resolve_stream('name', 'Ear_EEG_Right')
inlet_right = StreamInlet(streams[0])

# 接收数据
while True:
    sample_left, timestamp_left = inlet_left.pull_sample()
    sample_right, timestamp_right = inlet_right.pull_sample()
    
    print(f"左耳: {sample_left}, 右耳: {sample_right}")
```

### 使用 LabRecorder

1. 下载 LabRecorder: https://github.com/labstreaminglayer/App-LabRecorder
2. 运行程序启动 LSL 流
3. 打开 LabRecorder，选择要记录的流
4. 开始录制

### 在其他应用中使用

任何支持 LSL 的应用都可以接收这两个流的数据，例如：
- EEGLAB
- OpenViBE
- BrainVision Analyzer
- Neuromore Studio
- 等等

## 频率不同的处理说明

题目提到"左右耳不同频"，当前实现假设两耳采样率相同（500Hz）。如果实际采样率不同：

### 方案 1: 在硬件/驱动层处理（推荐）
确保设备驱动在发送数据前已处理好频率同步。

### 方案 2: 在应用层重采样
修改 `lsl_streamer.py` 中的 `create_streams()` 方法，为两个流设置不同的采样率：

```python
# 左耳 - 512Hz
left_info = StreamInfo(
    name='Ear_EEG_Left',
    nominal_srate=512,  # 左耳采样率
    ...
)

# 右耳 - 500Hz
right_info = StreamInfo(
    name='Ear_EEG_Right',
    nominal_srate=500,  # 右耳采样率
    ...
)
```

### 方案 3: 在接收端处理
接收应用可以读取LSL流的采样率元数据并自行处理同步。

## 故障排除

### 问题：LSL流创建失败

**症状**：看到 "LSL流创建失败" 的消息

**解决方案**：
1. 检查是否安装了 `pylsl` 库: `pip show pylsl`
2. 确保没有其他进程占用相同的流名称
3. 查看错误日志获取详细信息

### 问题：数据没有被推送到 LSL 流

**症状**：LSL 流已创建，但数据接收不到

**解决方案**：
1. 检查 `self.lsl_streamer.is_connected()` 返回值
2. 确保 BLE 数据接收正常运行
3. 在 `_handle_data_received` 中添加调试信息

### 问题：性能下降

**症状**：程序变慢，CPU使用率高

**解决方案**：
1. LSL 推送操作已使用锁保护，但仍可能有性能影响
2. 考虑降低推送频率或使用缓冲区
3. 修改 `push_left_chunk` 和 `push_right_chunk` 方法以支持批量推送

## 文件结构

```
src/devices/
├── lsl/
│   ├── __init__.py          # LSL模块初始化
│   └── lsl_streamer.py      # LSL流管理器核心代码
└── __init__.py              # 已更新，添加LSLStreamer导入
```

## API 参考

### LSLStreamer 类

```python
class LSLStreamer:
    def __init__(self, sample_rate=500):
        """初始化LSL流管理器"""
        
    def create_streams(self) -> bool:
        """创建左右耳的两个LSL流，返回True if成功"""
        
    def push_left_sample(self, sample: float):
        """推送左耳单个样本"""
        
    def push_right_sample(self, sample: float):
        """推送右耳单个样本"""
        
    def push_left_chunk(self, samples):
        """推送左耳多个样本（列表或numpy数组）"""
        
    def push_right_chunk(self, samples):
        """推送右耳多个样本（列表或numpy数组）"""
        
    def close_streams(self):
        """关闭所有LSL流"""
        
    def is_connected(self) -> bool:
        """检查是否已连接"""
```

## 更多信息

- LSL 官方文档: https://github.com/sccn/labstreaminglayer
- pylsl 文档: https://github.com/chkothe/pylsl
- LSL 应用列表: https://github.com/sccn/labstreaminglayer/wiki/Apps
