from pathlib import Path

from src.models.audio_task import AudioTask
from src.core.ffmpeg_service import FFmpegService


class AudioConverter:

    def __init__(self, ffmpeg_service: FFmpegService):
        self.ffmpeg = ffmpeg_service

    def convert(self, task: AudioTask):

        # 输入文件检查
        if not task.input_file.exists():
            raise FileNotFoundError(task.input_file)

        # 自动创建输出目录
        task.output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.ffmpeg.convert(task)