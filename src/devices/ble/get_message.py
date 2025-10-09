import asyncio
from bleak import BleakClient, BleakScanner
import struct
from typing import Union
import time
from PySide6.QtCore import QObject, QThread, Signal

from . import tools

# 全局通知处理器实例
notification_handler = tools.NotificationHandler()


class BluetoothDevice(QObject):
    data_received_signal = Signal(dict)
    device_info_signal = Signal(dict)

    def __init__(self, device_name):
        super().__init__()
        self.device_name = device_name
        self.client = None

        self.left_packet_count = 0
        self.right_packet_count = 0

    async def connect(self) -> str:
        '''
        根据设备名称连接设备，连接成功返回 ok， 否则返回失败原因
        需要注意的是，连接成功的话，设备信息会通过 notification_handler.handle_notification 处理
        现在是会打印出设备信息
        TODO : 在ui中显示设备信息
        '''
        print("正在扫描设备...")
        devices = await BleakScanner.discover()
        target = next((d for d in devices if d.name == self.device_name), None)

        if not target:
            print(f"未找到设备: {self.device_name}")
            return f"未找到设备: {self.device_name}"
        
        print(f"找到设备: {target.name}, 地址: {target.address}")

        try:
            self.client = BleakClient(target.address)
            await self.client.connect()

            # 启用通知
            await self.client.start_notify(tools.CMD_NOTIFY_UUID, self._handle_cmd)
            print("已启用命令通知")
            # 初始化 - 发送获取设备信息命令
            print("发送获取设备信息命令...")
            await self.client.write_gatt_char(tools.CMD_WRITE_UUID, tools.GET_INFO_CMD)
            # 等待命令响应
            await asyncio.sleep(1.0)

            return "ok"
        
        except Exception as e:
            self.client = None
            print(f"连接失败: {str(e)}")
            return f"连接失败: {str(e)}"
        

    async def _handle_cmd(self, sender, data):
        """处理通知数据"""
        sender_uuid = str(sender)

        if tools.CMD_NOTIFY_UUID in sender_uuid:
            res = notification_handler.handle_command_notification(data)
        elif tools.DATA_LEFT_NOTIFY_UUID in sender_uuid:
            return notification_handler.handle_data_notification(data, "left")
        elif tools.DATA_RIGHT_NOTIFY_UUID in sender_uuid:
            return notification_handler.handle_data_notification(data, "right")
        else:
            return print(f"CMD HANDLER收到未知特征通知: {data.hex(' ')}")
            
        
        if res and res['type'] == "device_info":
            self.device_info_signal.emit(res)
            


    async def get_messages(self):
        if self.client and not self.client.is_connected:
            await self.client.connect()

        print("still connect!")

        await self.client.start_notify(tools.DATA_LEFT_NOTIFY_UUID, self._handle_data)
        print("已启用左耳数据通知")

        await self.client.start_notify(tools.DATA_RIGHT_NOTIFY_UUID, self._handle_data)
        print("已启用右耳数据通知")

        # 发送打开数据命令
        print("发送打开数据命令，开始接收耳道信号...")
        await self.client.write_gatt_char(tools.CMD_WRITE_UUID, tools.OPEN_DATA_CMD)

        # 等待命令响应
        await asyncio.sleep(0.5)

        # 接收信号
        last_time = time.time()

        while True:
            await asyncio.sleep(0.02)  # 减少CPU占用，并且保持连接状态

            # 每秒更新时间
            current_time = time.time()
            if current_time - last_time >= 1:  # 每秒钟
                last_time = current_time
                # 每秒发射数据包数量
                print(f"左耳耳机每秒接收的数据包数量: {self.left_packet_count}")  # 输出到控制台
                print(f"右耳耳机每秒接收的数据包数量: {self.right_packet_count}")  # 输出到控制台
                # 重置包计数
                self.left_packet_count = 0
                self.right_packet_count = 0


    async def _handle_data(self, characteristic, data: bytearray):
        # 确定左右耳/信息数据
        characteristic = str(characteristic)
        if tools.DATA_LEFT_NOTIFY_UUID in characteristic:
            side = "left"
        elif tools.DATA_RIGHT_NOTIFY_UUID in characteristic:
            side = "right"
        else:
            print(f"DATA HANDLER收到未知特征通知: {data.hex(' ')}")
            return
        
        # 解析数据
        parse_result = tools.DataParser.parse_eeg_data(data, side)
        if parse_result:
            if side == "left":
                self.left_packet_count += 1
            else:
                self.right_packet_count += 1
            self.data_received_signal.emit(parse_result)


class BleConnectThread(QThread):
    finished = Signal(str)

    def __init__(self, ble_device):
        super().__init__()
        self.ble_device = ble_device

    def run(self):
        import asyncio
        res = asyncio.run(self.ble_device.connect())
        self.finished.emit(res)


class BleGetMessageThread(QThread):
    def __init__(self, ble_device):
        super().__init__()
        self.ble_device = ble_device

    def run(self):
        import asyncio
        asyncio.run(self.ble_device.get_messages())


if __name__ == "__main__":
    try:
        DEVICE_NAME = "Naoyun Pods BLE-3426"
        ble = BluetoothDevice(DEVICE_NAME)
        asyncio.run(ble.connect())
        if ble.client and ble.client.is_connected:
            print("let's get messages then")
            # asyncio.run(ble.get_messages())
        # if client and not client.is_connected:
        #     print("连接成功，按Ctrl+C断开连接")
        #     asyncio.run(asyncio.sleep(15))  # 保持连接15秒
        #     print("断开连接")
    except KeyboardInterrupt:
        print("程序被用户中断")