from PySide6.QtCore import QThread
from datetime import datetime
from ..utils import get_abs_path, write_dict_to_json
import numpy as np
import os


class SaveExpDataThread(QThread):

	def __init__(self):
		super().__init__()
		self.exp_left_data = None
		self.exp_right_data = None
		self.exp_info = None

	def run(self):
		# 文件夹和文件名 范式_当前时间
		folder_name = 'exp_data/'
		os.makedirs(get_abs_path(folder_name), exist_ok=True)
		file_name = f"exp_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
		# 将原实验信息和始数据写入文件
		np.save(get_abs_path(folder_name + file_name + '_left' + '.npy'), self.exp_left_data)
		np.save(get_abs_path(folder_name + file_name + '_right' + '.npy'), self.exp_right_data)
		write_dict_to_json(self.exp_info, get_abs_path(folder_name + file_name + '.json'))
		# 打包pickle文件
		# with open(folder_name + file_name + '.pkl', 'wb') as file:
		#     pickle.dump((self.exp_info, self.exp_data, self.exp_emg_data), file)

	def save_exp_data(self, exp_left_data, exp_right_data, exp_info):
		self.exp_left_data = exp_left_data
		self.exp_right_data = exp_right_data
		self.exp_info = exp_info
		self.start()