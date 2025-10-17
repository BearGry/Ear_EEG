import asyncio
from bleak import BleakClient, BleakScanner
import struct


# 命令服务
CMD_SERVICE_UUID = "30ae0100-0000-1000-8000-009034122420"
CMD_WRITE_UUID = "32ae0100-0000-1000-8000-009034122420"
CMD_NOTIFY_UUID = "31ae0100-0000-1000-8000-009034122420"

# 数据服务
DATA_SERVICE_UUID = "30ae0100-0000-1000-8000-009021091520"
DATA_LEFT_NOTIFY_UUID = "31ae0200-0000-1000-8000-009121091520"
DATA_RIGHT_NOTIFY_UUID = "32ae0300-0000-1000-8000-009221091520"

# 初始化命令
GET_INFO_CMD = bytes.fromhex("AA 55 00 E0 00 55 AA 26")
OPEN_DATA_CMD = bytes.fromhex("AA 55 01 01 00 55 AA 2D")

# 常量定义
MAX_MILLI_VOLT = 5000  # 最大量程：±2500mV
MAGNIFICATION = 1000.0 / 24  # 1000mV转uV，24倍放大系数
FULL_RANGE_DATA = 16777215  # 2^24-1，24bit最大值


class DataParser:
    """
    数据解析器：
        专门解析数据，返回信息字典
    """

    @staticmethod
    def crc8_maxim(data):
        """CRC8校验"""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8C
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def parse_device_info(data):
        """解析设备信息响应"""
        if len(data) < 16 or data[0:2] != b"\xAA\x55" or data[-3:-1] != b"\x55\xAA":
            return None

        # 检查CRC
        if DataParser.crc8_maxim(data[:-1]) != data[-1]:
            return None

        cmd_type = data[2:4].hex().upper()
        if cmd_type != "00E0":
            return None

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

        return info

    @staticmethod
    def parse_eeg_data(data, ear_side):
        """解析EEG数据包"""
        if len(data) < 10 or data[0:2] != b"\xAA\x55" or data[-3:-1] != b"\x55\xAA":
            return None

        # 检查CRC
        if DataParser.crc8_maxim(data[:-1]) != data[-1]:
            print(f"CRC校验失败")
            return None

        # 解析数据包头部
        protocol_cmd = data[2]
        ear_flag = data[3]  # 00左耳, 01右耳
        data_length = data[4]

        # 验证耳标志与传入参数的一致性
        expected_flag = 0 if ear_side == "left" else 1
        if ear_flag != expected_flag:
            print(f"耳标志不匹配: 期望={expected_flag}, 实际={ear_flag}")
            return None

        # 提取有效载荷 (50组24bit数据)
        payload = data[5:5 + data_length]

        # 提取附加信息
        lead_off = data[-5]  # 导联脱落检测位
        packet_count = data[-4]  # 数据包累加值

        # 解析EEG样本
        samples = []
        for i in range(0, len(payload), 3):
            if i + 3 > len(payload):
                break

            # 提取3字节样本
            sample_bytes = payload[i:i + 3]

            # 24bit转int (小端模式)
            value = (sample_bytes[2] << 16) | (sample_bytes[1] << 8) | sample_bytes[0]

            # 符号扩展
            if (value & (1 << 23)) > 0:
                value = (0xff << 24) | value

            # 转换为uV
            uV_value = value * MAX_MILLI_VOLT * MAGNIFICATION / FULL_RANGE_DATA
            samples.append(uV_value)

        result = {
            "ear_side": ear_side,
            "protocol_cmd": protocol_cmd,
            "data_length": data_length,
            "lead_off": lead_off,
            "packet_count": packet_count,
            "samples": samples,
            "sample_count": len(samples)
        }

        return result


class NotificationHandler:
    """通知处理器"""

    def __init__(self):
        self.device_info = None

    def handle_notification(self, sender, data):
        """处理通知数据"""
        sender_uuid = str(sender)

        if CMD_NOTIFY_UUID in sender_uuid:
            return self.handle_command_notification(data)
        elif DATA_LEFT_NOTIFY_UUID in sender_uuid:
            return self.handle_data_notification(data, "left")
        elif DATA_RIGHT_NOTIFY_UUID in sender_uuid:
            return self.handle_data_notification(data, "right")
        else:
            print(f"未知特征通知: {data.hex(' ')}")
            return None

    def handle_command_notification(self, data):
        """处理命令通知"""

        # 检查是否是打开数据命令的响应
        if len(data) >= 8 and data[0:2] == b"\xAA\x55" and data[2:4] == b"\x01\x01":
            print("=========数据流已成功开启========")
            return {"type": "data open", "status": "data_stream_enabled"}

        # 尝试解析设备信息
        device_info = DataParser.parse_device_info(data)
        if device_info:
            self.device_info = device_info
            self._print_device_info()
            return device_info

        return None

    def handle_data_notification(self, data, ear_side):
        """处理数据通知
        result = DataParser.parse_eeg_data(data, ear_side)
        if result:
            ear_name = "左耳" if ear_side == "left" else "右耳"
            print(f"{ear_name}数据: 样本数={result['sample_count']}, 包计数={result['packet_count']}, "
                  f"导联状态={result['lead_off']}, 前5样本={result['samples'][:5]}")
            return result
        else:
            print(f"{'左耳' if ear_side == 'left' else '右耳'}数据解析失败: {data.hex(' ')}")
            return None
        """
        print("=========CMD——HANDLE错误地接收到信息类数据包========")

    def _print_device_info(self):
        """打印设备信息"""
        if not self.device_info:
            return

        info = self.device_info
        ear_map = {1: "左耳", 2: "右耳", 3: "双耳左", 4: "双耳右"}
        wear_map = {0: "未佩戴", 1: "佩戴"}
        endian_map = {0: "小端", 1: "大端"}

        print("\n=== 设备信息 ===")
        print(f"耳类型: {ear_map.get(info['ear_type'], '未知')}")
        print(f"电量: 左耳={info['battery_left']}%, 右耳={info['battery_right']}%")
        print(
            f"佩戴状态: 左耳={wear_map.get(info['wear_left'], '未知')}, 右耳={wear_map.get(info['wear_right'], '未知')}")
        print(f"硬件版本: {info['hardware_version']}, 软件版本: {info['software_version']}")
        print(f"字节序: {endian_map.get(info['endian'], '未知')}")
        print(f"降噪设置: {info['noise_cancel']}")
        print(f"触控开关: {info['touch_control']}")
        print(f"自动播放停止: {info['auto_stop']}")
        print("================\n")