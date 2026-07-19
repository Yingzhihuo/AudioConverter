import json
from pathlib import Path


class ConfigManager:
    """读取和保存程序配置。"""

    DEFAULT_CONFIG = {
        "ffmpeg_path": "",
        "ffprobe_path": "",
        "default_output": "output"
    }

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = {}

        self.load()

    def load(self):
        """加载配置，不存在则创建默认配置。"""
        if not self.config_path.exists():
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

    def save(self):
        """保存配置。"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get(self, key: str):
        return self.config.get(key)

    def set(self, key: str, value):
        self.config[key] = value
        self.save()