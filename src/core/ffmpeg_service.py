from pathlib import Path
import subprocess

from src.models.audio_task import AudioTask


class FFmpegService:

    def __init__(self, ffmpeg_path: str):
        self.ffmpeg = Path(ffmpeg_path)

    def check_ffmpeg(self) -> bool:
        return self.ffmpeg.exists()

    def get_version(self) -> str:
        result = subprocess.run(
            [str(self.ffmpeg), "-version"],
            capture_output=True,
            text=True,
        )

        return result.stdout.splitlines()[0]

    def convert(self, task: AudioTask):
        command = [
            str(self.ffmpeg),
            "-y" if task.overwrite else "-n",
            "-i",
            str(task.input_file),
        ]

        if task.codec:
            command.extend([
                "-c:a",
                task.codec.ffmpeg_codec
            ])

        if task.bitrate:
            command.extend(["-b:a", task.bitrate])

        if task.sample_rate:
            command.extend(["-ar", str(task.sample_rate)])

        if task.channels:
            command.extend(["-ac", str(task.channels)])

        command.append(str(task.output_file))

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        return result