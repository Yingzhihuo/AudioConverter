from pathlib import Path

from src.models.audio_task import AudioTask
from src.core.ffmpeg_service import FFmpegService


class AudioConverter:

    def __init__(
        self,
        ffmpeg_service: FFmpegService
    ):
        self.ffmpeg = ffmpeg_service


    def convert(
        self,
        task: AudioTask
    ):


        if not task.input_file.exists():
            raise FileNotFoundError(
                f"输入文件不存在: {task.input_file}"
            )


        # 创建输出目录

        task.output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        # 调用 FFmpeg

        result = self.ffmpeg.convert(task)


        return result