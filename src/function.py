import asyncio
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread

from .devices import BluetoothDevice, BleConnectThread

class Function:
    def __init__(self, ui) -> None:
        self.ui = ui
        self.ble = None  # BLE 设备客户端
        self.connect_thread = None  # 连接线程

    
    def connect_ble(self):
        '''
        连接 BLE 设备，没有连接上的话给出提示
        连上的话给出设备信息,并使连接按钮不可再点击
        '''
        device_name = self.ui.btn_select_ble.currentText()
        self.ble = BluetoothDevice(device_name)
        self.connect_thread = BleConnectThread(self.ble)
        self.connect_thread.finished.connect(self._handle_connect_result_signal)
        self.connect_thread.start()

    def _handle_connect_result_signal(self, result):
        if result != "ok":
            # 连接失败的弹窗
            QMessageBox.warning(self.ui.page1, "连接失败", result)
        else:
            print("连接成功，你应该能够看到设备信息")
            # 连接按钮设置为不能再点击
            self.ui.btn_connect_ble.setEnabled(False)
            self.ui.btn_connect_ble.setText("已连接")
        


