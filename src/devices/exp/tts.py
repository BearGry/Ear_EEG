import threading
import pyttsx3


GLOBAL_TTS_LOCK = threading.Lock()

class TextToSpeechThread(threading.Thread):
    def __init__(self, text, rate=150, volume=0.9):
        """
        初始化语言播报线程
        :param text: 要播报的文字
        :param rate: 播报语速（默认150）
        :param volume: 播报音量（默认0.9，范围0.0~1.0）
        :param callback: 可选，播报完成后的回调函数
        """
        super().__init__()
        self.text = text
        self.rate = rate
        self.volume = volume
        self.tts_engine = pyttsx3.init()

    def run(self):
        """
        线程执行的语言播报逻辑
        """
        try:
            with GLOBAL_TTS_LOCK:  # 确保 TTS 引擎线程安全
                # print(f"线程 {self.name} 开始播报：{self.text}")
                self.tts_engine.setProperty('rate', self.rate)
                self.tts_engine.setProperty('volume', self.volume)
                self.tts_engine.say(self.text)
                self.tts_engine.runAndWait()
        except Exception as e:
            print(f"线程 {self.name}, 播报内容{self.text}, 播报出错：{e}")
        finally:
            # print(f"线程 {self.name} 播报完成")
            pass