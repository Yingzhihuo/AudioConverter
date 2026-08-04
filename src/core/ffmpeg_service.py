import json
import os
from pathlib import Path
import subprocess
import tempfile

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

    def _ffprobe_path(self) -> Path:
        """Return the ffprobe executable installed next to ffmpeg."""
        executable_name = "ffprobe.exe" if self.ffmpeg.suffix.lower() == ".exe" else "ffprobe"
        return self.ffmpeg.with_name(executable_name)

    def read_metadata(self, audio_file: Path) -> dict[str, str]:
        """Read the common tags displayed by Windows Explorer."""
        command = [
            str(self._ffprobe_path()),
            "-v",
            "error",
            "-show_entries",
            "format_tags",
            "-of",
            "json",
            str(audio_file),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "无法读取音频信息")

        raw_tags = json.loads(result.stdout or "{}").get("format", {}).get("tags", {})
        tags = {key.lower(): str(value) for key, value in raw_tags.items()}
        return {
            "title": tags.get("title", ""),
            "artist": tags.get("artist", tags.get("artists", "")),
            "album": tags.get("album", ""),
            "album_artist": tags.get("album_artist", tags.get("album artist", "")),
            "genre": tags.get("genre", ""),
            "date": tags.get("date", tags.get("year", "")),
            "track": tags.get("track", ""),
        }

    def update_metadata(self, audio_file: Path, metadata: dict[str, str]):
        """Update tags in place while copying all streams without re-encoding."""
        audio_file = Path(audio_file)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{audio_file.stem}_metadata_",
                suffix=audio_file.suffix,
                dir=audio_file.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

            command = [
                str(self.ffmpeg),
                "-y",
                "-i",
                str(audio_file),
                "-map",
                "0",
                "-map_metadata",
                "0",
                "-c",
                "copy",
            ]
            for key, value in metadata.items():
                command.extend(["-metadata", f"{key}={value}"])
            if audio_file.suffix.lower() == ".mp3":
                command.extend(["-id3v2_version", "3"])
            command.append(str(temporary_path))

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "无法保存音频信息")
            os.replace(temporary_path, audio_file)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def convert(self, task: AudioTask, log_callback=None):
        command = [
            str(self.ffmpeg),
            "-y" if task.overwrite else "-n",
            "-i",
            str(task.input_file),
        ]

        if task.codec:
            command.extend(["-c:a", task.codec.ffmpeg_codec])
        if task.bitrate:
            command.extend(["-b:a", task.bitrate])
        if task.sample_rate:
            command.extend(["-ar", str(task.sample_rate)])
        if task.channels:
            command.extend(["-ac", str(task.channels)])
        command.append(str(task.output_file))

        if log_callback:
            log_callback("执行命令: " + subprocess.list2cmdline(command))

        # FFmpeg 将大部分运行信息写入 stderr。合并输出后逐行发送到界面。
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
            raise RuntimeError("FFmpeg 转换失败（退出码 {}）".format(return_code))

        return subprocess.CompletedProcess(command, return_code, "\n".join(output_lines))

