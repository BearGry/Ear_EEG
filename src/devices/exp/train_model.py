from PySide6.QtCore import QThread, Signal
from ..utils import get_abs_path, band_pass_filter, load_and_preprocess_eegnet_data
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn

import torch.optim as optim
import os


class SaveModelThread(QThread):
	model_save_signal = Signal(object)

	def __init__(self):
		super().__init__()
		self.exp_left_data = None
		self.exp_right_data = None
		self.exp_info = None
		self.model = None
		self.model_save_path = ''
		self.epochs = 100


	def train_and_save_model(self, exp_left_data, exp_right_data, exp_info, model, model_type, epochs=100):
		self.exp_left_data = exp_left_data
		self.exp_right_data = exp_right_data
		self.exp_info = exp_info
		self.model = model
		self.model_save_path = get_abs_path(f'exp_models/{model_type}/weight.pth')
		self.epochs = epochs
		self.start()


	def run(self):
		self._train_and_save_model(self.exp_left_data, self.exp_right_data, self.exp_info, 
							 self.model, self.model_save_path, self.epochs)


	def _train_and_save_model(self, left_data, right_data, info, model, model_save_path, num_epochs=100):
		device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
		print(f"Using device: {device}")

		train_loader, val_loader = load_and_preprocess_eegnet_data(left_data, right_data, info)

		model = model.to(device)
		try:
			model.load_state_dict(torch.load(model_save_path))
			print("Loaded model weights from", model_save_path)
		except FileNotFoundError:
			print("No existing model weights file found. Initializing model from scratch.")

		optimizer = optim.Adam(model.parameters(), lr=0.0001, weight_decay=1e-3)
		criterion = nn.CrossEntropyLoss()

		# 记录损失和准确率
		train_losses = []
		val_losses = []
		train_accuracies = []
		val_accuracies = []

		model.train()
		for epoch in range(num_epochs):
			model.train()
			running_loss = 0.0
			correct_train = 0
			total_train = 0
			for inputs, labels in train_loader:
				inputs, labels = inputs.to(device), labels.to(device)
				optimizer.zero_grad()
				outputs = model(inputs)
				loss = criterion(outputs, labels)
				loss.backward()
				optimizer.step()
				running_loss += loss.item()

				_, predicted = torch.max(outputs.data, 1)
				total_train += labels.size(0)
				correct_train += (predicted == labels).sum().item()

			# 计算训练损失和准确率
			train_loss = running_loss / len(train_loader)
			train_accuracy = 100 * correct_train / total_train if total_train > 0 else 0

			train_losses.append(train_loss)
			train_accuracies.append(train_accuracy)

			print(f"Epoch {epoch + 1}/{num_epochs}, Loss: {train_loss}, Train Accuracy: {train_accuracy}%")

			# 验证阶段
			model.eval()
			val_loss = 0.0
			correct_val = 0
			total_val = 0
			with torch.no_grad():
				for inputs, labels in val_loader:
					inputs, labels = inputs.to(device), labels.to(device)
					outputs = model(inputs)
					loss = criterion(outputs, labels)
					val_loss += loss.item()
					_, predicted = torch.max(outputs.data, 1)
					print(predicted, labels)
					total_val += labels.size(0)
					correct_val += (predicted == labels).sum().item()

			# 计算验证损失和准确率
			avg_val_loss = val_loss / len(val_loader)
			val_accuracy = 100 * correct_val / total_val if total_val > 0 else 0

			val_losses.append(avg_val_loss)
			val_accuracies.append(val_accuracy)

			print(f"Validation Loss: {avg_val_loss}, Validation Accuracy: {val_accuracy}%")


		# 保存模型
		directory = os.path.dirname(model_save_path)
		if not os.path.exists(directory):
			os.makedirs(directory)
		torch.save(model.state_dict(), model_save_path)
		print(f"Model saved to {model_save_path}")

		# 绘制训练和验证的损失与准确率曲线
		plt.figure(figsize=(12, 5))

		# 绘制损失曲线
		plt.subplot(1, 2, 1)
		plt.plot(range(num_epochs), train_losses, label='Train Loss')
		plt.plot(range(num_epochs), val_losses, label='Validation Loss')
		plt.xlabel('Epochs')
		plt.ylabel('Loss')
		plt.title('Train and Validation Loss')
		plt.legend()

		# 绘制准确率曲线
		plt.subplot(1, 2, 2)
		plt.plot(range(num_epochs), train_accuracies, label='Train Accuracy')
		plt.plot(range(num_epochs), val_accuracies, label='Validation Accuracy')
		plt.xlabel('Epochs')
		plt.ylabel('Accuracy (%)')
		plt.title('Train and Validation Accuracy')
		plt.legend()

		# 显示图形
		plt.tight_layout()
		plt.savefig("eegnet.png")
    	#plt.show()



if __name__ == "__main__":
    import json

    model_save_path = '../exp_models/eegnet/explore.pth'
    left_data = np.load('../exp_data/explore_2025_09_23_11_54_14_left.npy')
    right_data = np.load('../exp_data/explore_2025_09_23_11_54_14_right.npy')
    with open("../exp_data/explore_2025_09_23_11_54_14.json", 'r', encoding='utf-8') as load_f:
        info = json.load(load_f)