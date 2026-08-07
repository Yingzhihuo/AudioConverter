import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.config.config_manager import ConfigManager
from src.core.ffmpeg_service import FFmpegService
from src.core.converter import AudioConverter
from ui.main_window import MainWindow


def resource_dir() -> Path:
    """返回源码资源目录或 PyInstaller 打包后的资源目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent


def find_ffmpeg(config: ConfigManager) -> Path:
    """优先使用有效的用户配置，否则使用项目内置 FFmpeg。"""
    configured_path = config.get("ffmpeg_path")

    if configured_path:
        configured_ffmpeg = Path(configured_path)
        if configured_ffmpeg.is_file():
            return configured_ffmpeg

    bundled_ffmpeg = resource_dir() / "tools" / "ffmpeg.exe"
    if bundled_ffmpeg.is_file():
        return bundled_ffmpeg

    raise FileNotFoundError(
        "未找到 FFmpeg。请确认程序包含 tools/ffmpeg.exe，"
        "或在设置中指定 FFmpeg 路径。"
    )


def main():
    config = ConfigManager()
    ffmpeg_path = find_ffmpeg(config)

    ffmpeg = FFmpegService(ffmpeg_path)
    converter = AudioConverter(ffmpeg)

    app = QApplication(sys.argv)

    window = MainWindow(
        converter,
        config,
        output_dir=config.get("default_output") or "output",
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()