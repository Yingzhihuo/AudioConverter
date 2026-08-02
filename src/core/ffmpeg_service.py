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

    def convert(self, task: AudioTask, log_callback=None):
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

        if log_callback:
            log_callback("执行命令: " + subprocess.list2cmdline(command))

        # ffmpeg 将大部分运行信息写入 stderr；合并两个流后逐行读取，调用方即可
        # 在转换尚未结束时把日志显示到界面中。
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        output_lines = []

        assert process.stdout is not None
        for line in process.stdout:
            message = line.rstrip()
            output_lines.append(message)
            if log_callback and message:
                log_callback(message)

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                "ffmpeg 转换失败（退出码 {}）".format(return_code)
            )

        return subprocess.CompletedProcess(command, return_code, "\n".join(output_lines))
