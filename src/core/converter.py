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
            task: AudioTask,
            log_callback=None,
            cancellation_event=None,
    ):

        if not task.input_file.exists():
            raise FileNotFoundError(
                task.input_file
            )

        task.output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        return self.ffmpeg.convert(
            task,
            log_callback=log_callback,
            cancellation_event=cancellation_event,
        )

    def cancel_current_conversion(self):
        return self.ffmpeg.cancel_current_conversion()

    def convert_batch(
            self,
            tasks: list[AudioTask]
    ):
        results = []

        for task in tasks:
            result = self.convert(
                task
            )

            results.append(
                result
            )

        return results
