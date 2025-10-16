import asyncio
import numpy as np
import random
import time
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem
from PySide6.QtCore import QThread, Signal, QObject

from .devices import BluetoothDevice, BleConnectThread, BleGetMessageThread, EEGPlotter
from .devices import ExperimentThread, TextToSpeechThread
from .devices import SaveExpDataThread, SaveModelThread, EEGNet



class Signals(QObject):
    left_plotter = Signal(list)  # 左耳数据绘图信号
    right_plotter = Signal(list)  # 右耳数据绘图信号


class Function:

    def __init__(self, ui) -> None:
        self.ui = ui
        self.ble = None  # BLE 设备客户端
        self.signals = Signals()

        self.connect_thread = None  # 连接线程
        self.get_message_thread = None  # 获取数据线程

        self.left_data = np.zeros((0))  # 左耳数据存储
        self.left_data_index = 0  # 左耳数据索引
        self.right_data = np.zeros((0))  # 右耳数据存储
        self.right_data_index = 0  # 右耳数据索引

        self.left_data_plotter = None  # 左耳绘图器
        self.right_data_plotter = None  # 右耳绘图器

        self.exp_thread = None  # 实验线程
        self.mark = [] # 实验标记
        self.save_expdata_thread = None # 储存实验数据
        self.model = None # 模型
        self.train_and_save_model_thread = None # 训练模型

        self.ACTION = {"闭眼": 0, "咬牙": 1, "左看": 2, "右看": 3}


    def start_experiment(self):
        '''
        开始实验按钮点击事件
        进行t轮实验，每轮4个动作，每个动作准备2秒，执行2秒，休息2秒
        '''
        self.ui.btn_start_exp.setText("实验进行中...")
        self.ui.btn_start_exp.setEnabled(False)

        self._reset_data()

        TextToSpeechThread("实验即将开始，请做好准备").start()

        epochs = self.ui.btn_exp_cnt.value()
        self.exp_thread = ExperimentThread(epochs=epochs, actions=list(self.ACTION.keys()))
        self.exp_thread.update_label_signal.connect(self._handle_update_label_signal)
        self.exp_thread.action_signal.connect(self._handle_action_signal) 
        self.exp_thread.exp_finished.connect(self._handle_exp_finished)
        self.exp_thread.start()

    def _reset_data(self):
        self.left_data = np.zeros((0))  # 左耳数据存储
        self.left_data_index = 0  # 左耳数据索引
        self.right_data = np.zeros((0))  # 右耳数据存储
        self.right_data_index = 0  # 右耳数据索引

    def _handle_update_label_signal(self, text, idx):
        speak = ["准备", "开始", "休息"]
        self.ui.label_exp_window.setText(text)
        TextToSpeechThread(speak[idx]).start()

    def _handle_action_signal(self, action):
        self.mark.append((self.left_data_index, self.right_data_index, self.ACTION[action]))
   
    def _handle_exp_finished(self):
        exp_left_data = self.left_data.copy()
        exp_right_data = self.right_data.copy()
        exp_info={
                "action_map": self.ACTION,
                "left_data_length": len(exp_left_data),
                "right_data_length": len(exp_right_data),
                "left_sample_rate": 500,
                "right_sample_rate": 500,
                "mark": self.mark,
            }
        # 保存实验数据(可用于后续离线数据处理)
        self.save_expdata_thread = SaveExpDataThread()
        self.save_expdata_thread.save_exp_data(
            exp_left_data=exp_left_data,
            exp_right_data=exp_right_data,
            exp_info=exp_info
        )

        # 在线的训练并保存模型（weight会替换）
        self.model = EEGNet(final_feature_dim=len(self.ACTION))
        self.train_and_save_model_thread = SaveModelThread()
        self.train_and_save_model_thread.train_and_save_model(
            exp_left_data=exp_left_data,
            exp_right_data=exp_right_data,
            exp_info=exp_info,
            model=self.model,
            model_type="EEGNet",
            epochs=100
        )

        QMessageBox.information(self.ui.page3, "实验结束", "实验结束，感谢您的参与！")
        self.ui.btn_start_exp.setText("开始实验")
        self.ui.btn_start_exp.setEnabled(True)


    def connect_ble(self):
        '''
        连接 BLE 设备，没有连接上的话给出提示
        连上的话给出设备信息,并使连接按钮不可再点击
        '''
        self.ui.btn_connect_ble.setEnabled(False)
        self.ui.btn_connect_ble.setText("连接中...")
        device_name = self.ui.btn_select_ble.currentText()
        self.ble = BluetoothDevice(device_name)
        self.connect_thread = BleConnectThread(self.ble)
        self.connect_thread.finished.connect(self._handle_connect_result_signal)
        self.ble.device_info_signal.connect(self._handle_device_info_signal)
        self.connect_thread.start()


    def _handle_connect_result_signal(self, result):
        if result != "ok":
            # 连接失败的弹窗
            QMessageBox.warning(self.ui.page1, "连接失败", result)
            self.ui.btn_connect_ble.setEnabled(True)
            self.ui.btn_connect_ble.setText("连接设备")
        else:
            print("连接成功，你应该能够看到设备信息")
            # 连接按钮设置为不能再点击
            self.ui.btn_connect_ble.setEnabled(False)
            self.ui.btn_connect_ble.setText("已连接")


    def _handle_device_info_signal(self, info):
        '''
        处理设备信息信号，显示在 ui 上
        info = {
            "type": "device_info",
            "ear_type": data[5],  # 01左耳, 02右耳, 03双耳左, 04双耳右
            "battery_left": data[6],  # 左耳电量 (0-100)
            "battery_right": data[7],  # 右耳电量 (0-100)
            "wear_left": data[8],  # 左耳佩戴状态 (0未佩戴, 1佩戴)
            "wear_right": data[9],  # 右耳佩戴状态 (0未佩戴, 1佩戴)
            "hardware_version": data[10],  # 硬件版本号
            "software_version": data[11],  # 软件版本号
            "endian": data[12],  # 大小端 (0小端, 1大端)
            "noise_cancel": data[13],  # 降噪开关 (0关, 1降噪, 2环境音)
            "touch_control": data[14],  # 触控开关 (0关闭, 1开启)
            "auto_stop": data[15],  # 自动播放停止功能 (0开启, 1关闭)
        }
        '''
        ear_map = {1: "左耳", 2: "右耳", 3: "双耳左", 4: "双耳右"}
        wear_map = {0: "未佩戴", 1: "佩戴"}
        endian_map = {0: "小端", 1: "大端"}
        noise_map = {0: "关闭", 1: "降噪", 2: "环境音"}
        touch_map = {0: "关闭", 1: "开启"}
        auto_map = {0: "开启", 1: "关闭"}

        stats = [
            ("耳类型", ear_map.get(info.get("ear_type"), "未知")),
            ("左耳佩戴", wear_map.get(info.get("wear_left"), "未知")),
            ("右耳佩戴", wear_map.get(info.get("wear_right"), "未知")),
            ("左耳电量", f"{info.get('battery_left', '-')} %"),
            ("右耳电量", f"{info.get('battery_right', '-')} %"),
            ("硬件版本", str(info.get("hardware_version", "未知"))),
            ("软件版本", str(info.get("software_version", "未知"))),
            ("字节序", endian_map.get(info.get("endian"), "未知")),
            ("降噪设置", noise_map.get(info.get("noise_cancel"), "未知")),
            ("触控开关", touch_map.get(info.get("touch_control"), "未知")),
            ("自动播放停止", auto_map.get(info.get("auto_stop"), "未知")),
        ]

        table = self.ui.table_ble_stats
        for row, (key, value) in enumerate(stats):
            table.setItem(row+1, 1, QTableWidgetItem(value))


    def get_message(self):
        '''
        获取左右耳的 EEG 数据，并分别存储到left_data 和 right_data 变量中，
        终端打印出每秒的包计数, 并且把数据传给绘图器进行实时绘图
        '''
        lowcut = self.ui.btn_lowcut_set.value()
        highcut = self.ui.btn_highcut_set.value()
        self.left_data_plotter = EEGPlotter(self.ui.left_plot_window, lowcut=lowcut, highcut=highcut)  # 左耳绘图器
        self.right_data_plotter = EEGPlotter(self.ui.right_plot_window, lowcut=lowcut, highcut=highcut, side="right")  # 右耳绘图器
        self.signals.left_plotter.connect(self.left_data_plotter.update_plot)
        self.signals.right_plotter.connect(self.right_data_plotter.update_plot)

        self.get_message_thread = BleGetMessageThread(self.ble)
        self.ble.data_received_signal.connect(self._handle_data_received)
        self.get_message_thread.start()
        self.ui.btn_get_message.setEnabled(False)
        self.ui.btn_get_message.setText("数据接收中...")


    def _handle_data_received(self, data):
        '''
        处理接收到的数据，存储到对应的变量中
        data: dict
        {
            "ear_side": ear_side,
            "protocol_cmd": protocol_cmd,
            "data_length": data_length,
            "lead_off": lead_off,
            "packet_count": packet_count,
            "samples": samples,
            "sample_count": len(samples)
        }
        '''
        if data["ear_side"] == "left":
            self.left_data = np.concatenate((self.left_data, np.array(data["samples"])))
            self.left_data_index += data["sample_count"]
            if self.left_data_index % 5000 == 0:
                print(f"左耳数据长度: {self.left_data_index}")
            self.signals.left_plotter.emit(data["samples"])
            
        elif data["ear_side"] == "right":
            self.right_data = np.concatenate((self.right_data, np.array(data["samples"])))
            self.right_data_index += data["sample_count"]
            if self.right_data_index % 5000 == 0:
                print(f"右耳数据长度: {self.right_data_index}")
            self.signals.right_plotter.emit(data["samples"])

